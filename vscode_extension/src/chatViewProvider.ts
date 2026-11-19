import * as crypto from 'crypto';
import * as fs from 'fs';
import * as os from 'os';
import * as path from 'path';
import * as vscode from 'vscode';
import { ConnectionManager } from './connectionManager';
import { buildLocalPreview } from './filePreview';
import { currentLanguage, isRtl, localeTag, onDidChangeLanguage, t } from './i18n';
import { ConnectionState, IncomingPayload } from './types';
import { WorkspaceBridge } from './workspaceBridge';

interface UploadingEntry {
  localId: string;
  filename: string;
  isImage: boolean;
}

/** Id of a preview asked by the view: the answer carries it back */
const REQUEST_ID = /^[\w.-]{1,64}$/;
/** Names of files a reply may cite, looked for in the workspace, at most */
const LINK_CANDIDATES_MAX = 200;

export class ChatViewProvider implements vscode.WebviewViewProvider {
  public static readonly viewType = 'myai-relay.chat';

  private view: vscode.WebviewView | null = null;
  private context: vscode.ExtensionContext;
  private manager: ConnectionManager;
  private bridge: WorkspaceBridge;
  private uploadingByLocalId = new Map<string, UploadingEntry>();
  private localIdCounter = 0;

  constructor(
    context: vscode.ExtensionContext,
    manager: ConnectionManager,
    bridge: WorkspaceBridge,
  ) {
    this.context = context;
    this.manager = manager;
    this.bridge = bridge;

    manager.on('state-changed', (state: ConnectionState) => {
      this.postState(state).catch(() => { /* webview may be closed */ });
      // The conversation itself follows the host's hello_ack (code_snapshot)
      if (state.kind === 'connected') {
        this.loadPrompts();
      }
    });
    manager.on('message', (payload: IncomingPayload) => {
      this.post({ type: 'relay-message', payload });
      if (payload.type === 'hello_ack') {
        // Shared conversation or not: the welcome text says it
        this.postState(this.manager.getState()).catch(() => { /* webview may be closed */ });
      }
    });
    manager.on('tool-event', (event: unknown) => {
      this.post({ type: 'tool-event', event });
    });
    // My_AI's language changed: the view speaks the new one at once
    context.subscriptions.push(onDidChangeLanguage(() => {
      this.post({ type: 'init-strings', ...webviewLanguage() })
        .then(() => this.postState(this.manager.getState()))
        .then(undefined, () => { /* webview may be closed */ });
    }));
  }

  resolveWebviewView(view: vscode.WebviewView): void {
    this.view = view;
    view.webview.options = {
      enableScripts: true,
      localResourceRoots: [vscode.Uri.joinPath(this.context.extensionUri, 'media')],
    };
    view.webview.html = this.renderHtml(view.webview);

    view.webview.onDidReceiveMessage((msg: unknown) => {
      this.handleWebviewMessage(msg).catch((err) => {
        // eslint-disable-next-line no-console
        console.error('[my-ai-relay] webview message failed:', err);
      });
    });

    view.onDidDispose(() => {
      this.view = null;
    });
  }

  reveal(): void {
    if (this.view) {
      this.view.show(true);
    } else {
      vscode.commands.executeCommand('myai-relay.chat.focus');
    }
  }

  private async handleWebviewMessage(msg: unknown): Promise<void> {
    if (!msg || typeof msg !== 'object') {
      return;
    }
    const m = msg as { type: string } & Record<string, unknown>;
    switch (m.type) {
      case 'webview-ready':
        await this.post({ type: 'init-strings', ...webviewLanguage() });
        await this.postState(this.manager.getState());
        await this.post({ type: 'auto-attach-state', value: this.bridge.isAutoAttachEnabled() });
        if (this.manager.getState().kind === 'connected') {
          // View reloaded: the whole conversation again, from the host
          await this.manager.requestConversation().catch(() => { /* reconnecting */ });
          this.loadPrompts();
        }
        break;
      case 'clear-chat':
        // New conversation everywhere; an older host (or none) only clears this view
        if (!(await this.manager.clearConversation().catch(() => false))) {
          await this.post({ type: 'clear-local' });
        }
        break;
      case 'approve-tool':
        if (typeof m.callId === 'string' && typeof m.decision === 'string') {
          this.manager.approveTool(m.callId, m.decision);
        }
        break;
      case 'connect-request':
        await vscode.commands.executeCommand('myai-relay.connect');
        break;
      case 'send-chat':
        await this.handleSendChat(
          typeof m.text === 'string' ? m.text : '',
          Array.isArray(m.fileIds) ? (m.fileIds as string[]) : [],
        );
        break;
      case 'pick-file':
        await this.handlePickFile();
        break;
      case 'mention-query':
        await this.handleMentionQuery(typeof m.query === 'string' ? m.query : '');
        break;
      case 'attach-mention':
        await this.handleAttachMention(
          typeof m.kind === 'string' ? m.kind : '',
          typeof m.path === 'string' ? m.path : '',
        );
        break;
      case 'remove-attachment':
        if (typeof m.localId === 'string') {
          this.uploadingByLocalId.delete(m.localId);
        }
        break;
      case 'set-auto-attach':
        await this.bridge.setAutoAttach(!!m.value);
        await this.post({ type: 'auto-attach-state', value: this.bridge.isAutoAttachEnabled() });
        break;
      case 'insert-at-cursor':
        if (typeof m.code === 'string') {
          await this.bridge.insertAtCursor(m.code);
        }
        break;
      case 'copy-to-clipboard':
        if (typeof m.text === 'string') {
          await vscode.env.clipboard.writeText(m.text);
        }
        break;
      case 'stop-generation':
        await this.manager.stopGeneration(
          typeof m.messageId === 'string' ? m.messageId : '',
        );
        break;
      case 'preview-file':
        await this.handlePreviewFile(m);
        break;
      case 'save-file':
        await this.handleSaveFile(m);
        break;
      case 'open-in-editor':
        if (typeof m.path === 'string' && m.path) {
          await vscode.commands.executeCommand('vscode.open', vscode.Uri.file(m.path));
        }
        break;
      case 'open-browser':
        if (typeof m.html === 'string' && m.html) {
          await this.openInBrowser(m.html);
        }
        break;
      case 'resolve-links':
        await this.handleResolveLinks(m);
        break;
    }
  }

  // ── Aperçu d'un fichier (modale de la vue, media/preview.js) ──────────────

  /**
   * Preview asked by the view. A file of this machine (workspace, attachment
   * picked here) is read here; a file of the PC (attachment sent, file of the
   * conversation) is asked to the Relay (`file_preview`), whose answer reaches
   * the view as a relay message. PDF, Word, Excel and PowerPoint files are
   * rendered by My_AI on the PC, as on the phone: sent there first.
   */
  private async handlePreviewFile(m: Record<string, unknown>): Promise<void> {
    const requestId = typeof m.requestId === 'string' ? m.requestId : '';
    if (!REQUEST_ID.test(requestId)) {
      return;
    }
    const answer = (payload: Record<string, unknown>) =>
      this.post({ type: 'file-preview', requestId, payload });
    try {
      if (typeof m.localPath === 'string' && m.localPath) {
        const uri = vscode.Uri.file(m.localPath);
        const preview = await buildLocalPreview(uri);
        if (preview.upload) {
          const data = await vscode.workspace.fs.readFile(uri);
          const sent = await this.manager.uploadFile(path.basename(uri.fsPath), new Uint8Array(data));
          await this.manager.requestFilePreview({ request_id: requestId, file_id: sent.fileId });
          return;
        }
        await answer(preview);
        return;
      }
      const request: Record<string, unknown> = { request_id: requestId };
      if (typeof m.fileId === 'string' && m.fileId) {
        request.file_id = m.fileId;
      } else if (typeof m.path === 'string' && m.path) {
        request.path = m.path;
      } else {
        await answer({ ok: false, error: t('File not found.') });
        return;
      }
      if (m.download === true) {
        request.download = true;
      }
      await this.manager.requestFilePreview(request);
    } catch (err) {
      await answer({ ok: false, error: (err as Error).message });
    }
  }

  /** File of the PC (Download in the preview): saved where the user says */
  private async handleSaveFile(m: Record<string, unknown>): Promise<void> {
    if (typeof m.data !== 'string' || !m.data) {
      return;
    }
    const name = path.basename(typeof m.name === 'string' && m.name ? m.name : 'file');
    const folder = vscode.workspace.workspaceFolders?.[0]?.uri
      ?? vscode.Uri.file(os.homedir());
    const target = await vscode.window.showSaveDialog({
      defaultUri: vscode.Uri.joinPath(folder, name),
      saveLabel: t('Save'),
    });
    if (!target) {
      return;
    }
    await vscode.workspace.fs.writeFile(target, Buffer.from(m.data, 'base64'));
  }

  /** Web page of a reply, in the browser: its scripts run as written there */
  private async openInBrowser(html: string): Promise<void> {
    const file = path.join(os.tmpdir(), `my-ai-preview-${crypto.randomBytes(6).toString('hex')}.html`);
    await fs.promises.writeFile(file, html, 'utf-8');
    await vscode.env.openExternal(vscode.Uri.file(file));
  }

  /**
   * Files of the workspace a finished reply cites (path) or names (file
   * name alone): clickable in the view, like the files of an answer of
   * My_AI's chat. A name alone counts when one file only bears it, or one of
   * those the reply's tools read or wrote.
   */
  private async handleResolveLinks(m: Record<string, unknown>): Promise<void> {
    const messageId = typeof m.messageId === 'string' ? m.messageId : '';
    if (!messageId) {
      return;
    }
    const candidates = (Array.isArray(m.candidates) ? m.candidates : [])
      .filter((item): item is string => typeof item === 'string' && item.length > 0 && item.length < 400)
      .slice(0, LINK_CANDIDATES_MAX);
    const touched = (Array.isArray(m.touched) ? m.touched : [])
      .filter((item): item is string => typeof item === 'string' && item.length > 0)
      .slice(0, 200);
    const links: { text: string; path: string; whole?: boolean }[] = [];
    if (candidates.length && vscode.workspace.workspaceFolders?.length) {
      const seen = new Set<string>();
      for (const candidate of candidates) {
        if (seen.has(candidate)) continue;
        seen.add(candidate);
        const found = await this.findWorkspaceFile(candidate, touched);
        if (found) {
          links.push({ text: candidate, path: found.fsPath, whole: !/[\\/]/.test(candidate) });
        }
      }
    }
    await this.post({ type: 'links', messageId, links });
  }

  private async isFile(uri: vscode.Uri): Promise<boolean> {
    try {
      return ((await vscode.workspace.fs.stat(uri)).type & vscode.FileType.File) !== 0;
    } catch {
      return false;
    }
  }

  private async findWorkspaceFile(candidate: string, touched: string[]): Promise<vscode.Uri | null> {
    const folders = vscode.workspace.workspaceFolders ?? [];
    const cleaned = candidate.replace(/^\.[\\/]/, '');
    if (path.isAbsolute(cleaned)) {
      const uri = vscode.Uri.file(cleaned);
      return (await this.isFile(uri)) ? uri : null;
    }
    const parts = cleaned.split(/[\\/]+/).filter(Boolean);
    if (!parts.length || parts.includes('..')) {
      return null;
    }
    if (parts.length > 1) {
      for (const folder of folders) {
        // Several folders open: « api/src/x.ts » may begin with the folder's name
        const tries = [parts];
        if (folders.length > 1 && parts[0] === folder.name) tries.push(parts.slice(1));
        for (const segments of tries) {
          const uri = vscode.Uri.joinPath(folder.uri, ...segments);
          if (await this.isFile(uri)) return uri;
        }
      }
      return null;
    }
    // A name alone: the file of that name the reply's tools touched (none when
    // they touched several: « utils.py » of tests/ and of src/, as on the PC),
    // else the only one of the workspace
    const name = parts[0].toLowerCase();
    const used = new Map<string, vscode.Uri>();
    for (const item of touched) {
      if (path.basename(item.replace(/\\/g, '/')).toLowerCase() !== name) continue;
      const found = await this.findWorkspaceFile(item, []);
      if (found) used.set(found.toString(), found);
    }
    if (used.size) {
      return used.size === 1 ? used.values().next().value ?? null : null;
    }
    const matches = (await this.getWorkspaceFiles())
      .filter((uri) => path.basename(uri.fsPath).toLowerCase() === name);
    return matches.length === 1 ? matches[0] : null;
  }

  private async handleSendChat(text: string, fileIds: string[]): Promise<void> {
    let allFileIds = fileIds.slice();
    try {
      const autoIds = await this.bridge.maybeAutoAttachActiveFile();
      allFileIds = autoIds.concat(allFileIds);
    } catch (err) {
      vscode.window.showWarningMessage(
        t('My_AI Relay: auto-attach failed: {0}', (err as Error).message),
      );
    }
    try {
      await this.manager.sendChat(text, allFileIds);
    } catch (err) {
      await this.post({ type: 'send-failed' });
      vscode.window.showErrorMessage(
        t('My_AI Relay: send failed: {0}', (err as Error).message),
      );
    }
  }

  private async handlePickFile(): Promise<void> {
    const picks = await vscode.window.showOpenDialog({
      canSelectMany: true,
      openLabel: t('Send to My_AI'),
      filters: {
        [t('All supported')]: [
          'pdf', 'docx', 'doc', 'xlsx', 'xls', 'pptx', 'potx', 'csv',
          'png', 'jpg', 'jpeg', 'gif', 'bmp', 'webp', 'tiff', 'tif',
          'py', 'js', 'ts', 'tsx', 'jsx', 'html', 'css', 'json', 'xml', 'md', 'txt',
        ],
      },
    });
    if (!picks || picks.length === 0) {
      return;
    }
    for (const uri of picks) {
      await this.uploadAndAnnounce(uri);
    }
  }

  // ── Mentions « @ » : fichiers et dossiers du workspace VS Code ───────────

  /** Cache court des fichiers du workspace pour l'autocomplétion « @ ». */
  private mentionCache: { time: number; files: vscode.Uri[] } | null = null;

  private async getWorkspaceFiles(): Promise<vscode.Uri[]> {
    const now = Date.now();
    if (this.mentionCache && now - this.mentionCache.time < 15000) {
      return this.mentionCache.files;
    }
    const exclude =
      '**/{node_modules,.git,.hg,.svn,dist,build,out,.venv,venv,env,' +
      '__pycache__,.mypy_cache,.pytest_cache,.next,.nuxt,.cache,coverage,' +
      'target,bin,obj,.idea,.vscode}/**';
    let files: vscode.Uri[] = [];
    try {
      files = await vscode.workspace.findFiles('**/*', exclude, 5000);
    } catch {
      files = [];
    }
    this.mentionCache = { time: now, files };
    return files;
  }

  private async handleMentionQuery(query: string): Promise<void> {
    const roots = vscode.workspace.workspaceFolders;
    if (!roots || roots.length === 0) {
      await this.post({ type: 'mention-results', query, items: [] });
      return;
    }

    const wsFiles = await this.getWorkspaceFiles();

    // Index : fichiers (rel POSIX + chemin absolu) et dossiers (rel -> abs),
    // ces derniers déduits des ancêtres des fichiers (dossiers non vides).
    type Item = { kind: string; label: string; detail: string; path: string; action?: string };
    const files: { label: string; rel: string; abs: string }[] = [];
    const folderAbs = new Map<string, string>(); // relPosix -> absFsPath
    for (const uri of wsFiles) {
      const rel = vscode.workspace.asRelativePath(uri, false).replace(/\\/g, '/');
      files.push({ label: path.basename(uri.fsPath), rel, abs: uri.fsPath });
      let relDir = rel.includes('/') ? rel.slice(0, rel.lastIndexOf('/')) : '';
      let absDir = path.dirname(uri.fsPath);
      while (relDir) {
        if (!folderAbs.has(relDir)) {
          folderAbs.set(relDir, absDir);
        }
        const slash = relDir.lastIndexOf('/');
        if (slash < 0) break;
        relDir = relDir.slice(0, slash);
        absDir = path.dirname(absDir);
      }
    }

    const baseName = (rel: string): string => rel.split('/').pop() || rel;
    const raw = query.replace(/\\/g, '/');
    const slashIdx = raw.lastIndexOf('/');
    const dirRel = slashIdx >= 0 ? raw.slice(0, slashIdx) : '';
    const tail = (slashIdx >= 0 ? raw.slice(slashIdx + 1) : raw).toLowerCase();
    const match = (s: string): boolean => !tail || s.toLowerCase().includes(tail);

    const items: Item[] = [];

    if (dirRel) {
      // ── Navigation DANS un dossier : enfants directs + « attacher ce dossier »
      const attachAbs = folderAbs.get(dirRel);
      if (attachAbs) {
        items.push({ kind: 'folder', action: 'attach', label: baseName(dirRel),
          detail: dirRel, path: attachAbs });
      }
      const prefix = dirRel + '/';
      const childFolders = new Set<string>();
      const childFiles: Item[] = [];
      for (const f of files) {
        if (!f.rel.startsWith(prefix)) continue;
        const rest = f.rel.slice(prefix.length);
        const sl = rest.indexOf('/');
        if (sl < 0) {
          if (match(rest)) {
            childFiles.push({ kind: 'file', label: f.label, detail: f.rel, path: f.abs });
          }
        } else {
          childFolders.add(prefix + rest.slice(0, sl));
        }
      }
      for (const fr of Array.from(childFolders).sort()) {
        if (match(baseName(fr))) {
          items.push({ kind: 'folder', action: 'navigate', label: baseName(fr),
            detail: fr, path: folderAbs.get(fr) || '' });
        }
        if (items.length >= 30) break;
      }
      for (const it of childFiles) {
        items.push(it);
        if (items.length >= 40) break;
      }
    } else {
      // ── Niveau racine / recherche globale : dossiers de 1er niveau (navigables)
      // + fichiers correspondants n'importe où (permet d'atteindre un fichier
      // imbriqué en tapant son nom).
      const topFolders = Array.from(folderAbs.keys())
        .filter((rel) => !rel.includes('/') && match(baseName(rel)))
        .sort();
      for (const fr of topFolders.slice(0, 6)) {
        items.push({ kind: 'folder', action: 'navigate', label: baseName(fr),
          detail: fr, path: folderAbs.get(fr) || '' });
      }
      const ranked = files
        .filter((f) => !tail || f.label.toLowerCase().includes(tail)
          || f.rel.toLowerCase().includes(tail))
        .map((f) => {
          const lbl = f.label.toLowerCase();
          const r = !tail ? 0 : lbl === tail ? 0 : lbl.startsWith(tail) ? 1
            : lbl.includes(tail) ? 2 : 3;
          return { f, r };
        })
        .sort((a, b) => a.r - b.r || a.f.rel.length - b.f.rel.length)
        .slice(0, 20 - items.length);
      for (const { f } of ranked) {
        items.push({ kind: 'file', label: f.label, detail: f.rel, path: f.abs });
      }
    }

    await this.post({ type: 'mention-results', query, items: items.slice(0, 30) });
  }

  private async handleAttachMention(_kind: string, fsPath: string): Promise<void> {
    if (!fsPath) {
      return;
    }
    // Fichier comme dossier : on passe par le canal d'indexation (@codebase),
    // fiable et cohérent avec le contexte du workspace. (Le bouton « + » reste
    // disponible pour joindre un fichier en pièce jointe ponctuelle.)
    await this.bridge.attachCodebasePath(fsPath);
  }

  private async uploadAndAnnounce(uri: vscode.Uri): Promise<void> {
    const localId = `att_${++this.localIdCounter}`;
    const filename = path.basename(uri.fsPath);
    const ext = path.extname(filename).toLowerCase();
    const isImage = ['.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp', '.tiff', '.tif'].includes(ext);

    this.uploadingByLocalId.set(localId, { localId, filename, isImage });
    await this.post({
      type: 'attachment-uploading',
      localId,
      name: filename,
      isImage,
    });

    try {
      const raw = await vscode.workspace.fs.readFile(uri);
      const result = await this.manager.uploadFile(filename, new Uint8Array(raw));
      await this.post({
        type: 'attachment-ready',
        localId,
        fileId: result.fileId,
        filename: result.filename,
        isImage: result.isImage,
        // On this machine: « Open in editor » in its preview
        path: uri.scheme === 'file' ? uri.fsPath : '',
      });
    } catch (err) {
      await this.post({
        type: 'attachment-error',
        localId,
        error: (err as Error).message,
      });
    }
  }

  private async loadPrompts(): Promise<void> {
    try {
      const items = await this.manager.loadPrompts();
      await this.post({ type: 'prompts', items });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('[my-ai-relay] loadPrompts failed:', err);
    }
  }

  private async postState(state: ConnectionState): Promise<void> {
    const hasCredentials = await this.manager.hasSavedCredentials();
    await this.post({
      type: 'state',
      state,
      hasCredentials,
      shared: this.manager.sharesConversation,
    });
  }

  private post(message: unknown): Thenable<boolean> {
    if (!this.view) {
      return Promise.resolve(false);
    }
    return this.view.webview.postMessage(message);
  }

  private renderHtml(webview: vscode.Webview): string {
    const mediaRoot = vscode.Uri.joinPath(this.context.extensionUri, 'media');
    const uri = (file: string) => webview.asWebviewUri(vscode.Uri.joinPath(mediaRoot, file)).toString();
    const nonce = crypto.randomBytes(16).toString('base64');

    const htmlPath = vscode.Uri.joinPath(mediaRoot, 'chat.html').fsPath;
    let html = fs.readFileSync(htmlPath, 'utf-8');
    // markdown.js, turn.js, preview.js and thread.css: the same files as the
    // phone page of the Relay (relay/static/), for the same rendering of the
    // replies and the same previews
    html = html
      .replace(/%CSP_SOURCE%/g, webview.cspSource)
      .replace(/%NONCE%/g, nonce)
      .replace(/%THREAD_CSS_URI%/g, uri('thread.css'))
      .replace(/%CHAT_CSS_URI%/g, uri('chat.css'))
      .replace(/%MARKDOWN_JS_URI%/g, uri('markdown.js'))
      .replace(/%TURN_JS_URI%/g, uri('turn.js'))
      .replace(/%PREVIEW_JS_URI%/g, uri('preview.js'))
      .replace(/%CHAT_JS_URI%/g, uri('chat.js'));
    return html;
  }
}

/**
 * Strings of the webview in My_AI's language, with what the page needs to
 * show it: language and direction of the document (Arabic is written right
 * to left), and the locale of the times. Posted right after `webview-ready`,
 * and again when My_AI's language changes.
 */
function webviewLanguage(): {
  strings: Record<string, string>;
  lang: string;
  dir: 'rtl' | 'ltr';
  locale: string;
} {
  return {
    strings: getWebviewStrings(),
    lang: currentLanguage(),
    dir: isRtl() ? 'rtl' : 'ltr',
    locale: localeTag(),
  };
}

/**
 * Build the bundle of localized strings consumed by the webview. The
 * webview-side keys are stable internal identifiers, but each localized
 * value is produced by `t(<English source string>)`, whose catalogs
 * (`l10n/<language>.json`) key on source strings, NOT abstract identifiers.
 */
function getWebviewStrings(): Record<string, string> {
  return {
    'webview.status.disconnected': t('Disconnected'),
    'webview.status.connecting': t('Connecting…'),
    'webview.status.reconnecting': t('Reconnecting…'),
    'webview.status.connected': t('Connected'),
    'webview.status.notConnected': t('Not connected'),
    'webview.banner.connectionLost': t('Connection lost. Trying to reconnect…'),
    'webview.connect.title': t('Not connected'),
    'webview.connect.description': t(
      'Start the Relay on your My_AI host PC, click "Copy" in the Relay panel once a tunnel is active, paste the link here, then enter the access code shown under the QR code.',
    ),
    'webview.connect.button': t('Paste connection string…'),
    'webview.connect.hint': t('Your credentials stay encrypted in VS Code SecretStorage.'),
    'webview.welcome.title': 'My_AI Relay',
    'webview.welcome.text': t(
      'Connected to your self-hosted assistant. Type a message to start.',
    ),
    'webview.welcome.shared': t(
      'This conversation also shows on the Code page of My_AI and on your phone: a message typed there acts here too.',
    ),
    'webview.header.autoAttachTooltip': t(
      'Auto-attach the active editor file to every message',
    ),
    'webview.header.autoAttachOn': t('Auto-attach: on'),
    'webview.header.autoAttachOff': t('Auto-attach: off'),
    'webview.header.clearTooltip': t(
      'New conversation: also clears it on the Code page of My_AI and on the phone',
    ),
    'webview.header.clear': t('Clear'),
    'webview.header.reconnect': t('New connection'),
    'webview.header.reconnectTooltip': t(
      'Paste a new connection string (use this if you restarted the Relay and the token changed)',
    ),
    'webview.input.placeholder': t('Type your message…'),
    'webview.input.attachTooltip': t('Attach a file or image'),
    'webview.mention.attachFolder': t('attach this folder'),
    'webview.send.stopTooltip': t('Stop generation'),
    'webview.code.insert': t('Insert'),
    'webview.code.copy': t('Copy'),
    'webview.code.inserted': t('Inserted!'),
    'webview.code.copied': t('Copied!'),
    'webview.attachment.remove': t('Remove'),
    'webview.attachment.error': t('error'),
    'webview.origin.desktop': t('From My_AI on the PC'),
    'webview.origin.mobile': t('From the phone'),
    // Preview of a file or of an HTML/SVG block (media/preview.js): a modal
    // over the view. {error} is filled in by the page
    'webview.preview.button': t('Preview'),
    'webview.preview.code': t('Code'),
    'webview.preview.close': t('Close'),
    'webview.preview.previous': t('Previous'),
    'webview.preview.next': t('Next'),
    'webview.preview.download': t('Download'),
    'webview.preview.openBrowser': t('Open in browser'),
    'webview.preview.openEditor': t('Open in editor'),
    'webview.preview.loading': t('Loading the preview…'),
    'webview.preview.none': t('No preview for this type of file.'),
    'webview.preview.failed': t('Preview unavailable: {error}'),
    'webview.preview.truncated': t('Only the beginning of the file is shown.'),
    'webview.preview.offline': t('Not connected to My_AI.'),
    'webview.preview.timeout': t('My_AI did not answer in time.'),
    // Replies, drawn by media/turn.js as on the phone: the keys of its page.
    // {target} (path, pattern or command) and {0} (name of the tool) are
    // filled in by the page
    'code.tool.read_file': t('Reading {target}'),
    'code.tool.write_file': t('Writing {target}'),
    'code.tool.edit_file': t('Editing {target}'),
    'code.tool.list_dir': t('Listing {target}'),
    'code.tool.glob': t('Finding files {target}'),
    'code.tool.grep': t('Searching “{target}”'),
    'code.tool.run_command': t('Command: {target}'),
    'code.tool.get_active_editor': t('File open in VS Code'),
    'code.tool.open_file': t('Opening {target}'),
    'code.tool.input': t('Input'),
    'code.tool.output': t('Output'),
    'code.tool.empty': t('(empty)'),
    'code.toolStatus.awaiting': t('waiting for approval'),
    'code.toolStatus.failed': t('error'),
    'code.toolStatus.denied': t('denied'),
    'code.toolStatus.stopped': t('stopped'),
    'code.approval.prompt': t('Allow this action?'),
    'code.approval.allowOnce': t('Allow once'),
    'code.approval.allowTarget': t('Allow for this file'),
    'code.approval.allowTool': t('Allow all {0} this session'),
    'code.approval.deny': t('Deny'),
    'code.stopped': t('Reply interrupted'),
  };
}
