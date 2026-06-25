import * as crypto from 'crypto';
import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';
import { ConnectionManager } from './connectionManager';
import { ConnectionState, IncomingPayload } from './types';
import { WorkspaceBridge } from './workspaceBridge';

interface UploadingEntry {
  localId: string;
  filename: string;
  isImage: boolean;
}

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
      if (state.kind === 'connected') {
        this.loadHistory();
        this.loadPrompts();
      }
    });
    manager.on('message', (payload: IncomingPayload) => {
      this.post({ type: 'relay-message', payload });
    });
    manager.on('tool-event', (event: unknown) => {
      this.post({ type: 'tool-event', event });
    });
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
        await this.post({ type: 'init-strings', strings: getWebviewStrings() });
        await this.postState(this.manager.getState());
        await this.post({ type: 'auto-attach-state', value: this.bridge.isAutoAttachEnabled() });
        if (this.manager.getState().kind === 'connected') {
          this.loadHistory();
          this.loadPrompts();
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
    }
  }

  private async handleSendChat(text: string, fileIds: string[]): Promise<void> {
    let allFileIds = fileIds.slice();
    try {
      const autoIds = await this.bridge.maybeAutoAttachActiveFile();
      allFileIds = autoIds.concat(allFileIds);
    } catch (err) {
      vscode.window.showWarningMessage(
        vscode.l10n.t('warning.autoAttachFailed', (err as Error).message),
      );
    }
    try {
      await this.manager.sendChat(text, allFileIds);
    } catch (err) {
      vscode.window.showErrorMessage(
        vscode.l10n.t('error.sendFailed', (err as Error).message),
      );
    }
  }

  private async handlePickFile(): Promise<void> {
    const picks = await vscode.window.showOpenDialog({
      canSelectMany: true,
      openLabel: vscode.l10n.t('openDialog.openLabel'),
      filters: {
        [vscode.l10n.t('openDialog.filter.allSupported')]: [
          'pdf', 'docx', 'doc', 'xlsx', 'xls', 'csv',
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
      });
    } catch (err) {
      await this.post({
        type: 'attachment-error',
        localId,
        error: (err as Error).message,
      });
    }
  }

  private async loadHistory(): Promise<void> {
    try {
      const items = await this.manager.loadHistory();
      await this.post({ type: 'history', items });
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('[my-ai-relay] loadHistory failed:', err);
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
    await this.post({ type: 'state', state, hasCredentials });
  }

  private post(message: unknown): Thenable<boolean> {
    if (!this.view) {
      return Promise.resolve(false);
    }
    return this.view.webview.postMessage(message);
  }

  private renderHtml(webview: vscode.Webview): string {
    const mediaRoot = vscode.Uri.joinPath(this.context.extensionUri, 'media');
    const cssUri = webview.asWebviewUri(vscode.Uri.joinPath(mediaRoot, 'chat.css'));
    const jsUri = webview.asWebviewUri(vscode.Uri.joinPath(mediaRoot, 'chat.js'));
    const nonce = crypto.randomBytes(16).toString('base64');

    const htmlPath = vscode.Uri.joinPath(mediaRoot, 'chat.html').fsPath;
    let html = fs.readFileSync(htmlPath, 'utf-8');
    html = html
      .replace(/%CSP_SOURCE%/g, webview.cspSource)
      .replace(/%NONCE%/g, nonce)
      .replace(/%CHAT_CSS_URI%/g, cssUri.toString())
      .replace(/%CHAT_JS_URI%/g, jsUri.toString());
    return html;
  }
}

/**
 * Build the bundle of localized strings consumed by the webview. The
 * webview-side keys are stable internal identifiers, but each localized
 * value is produced by `vscode.l10n.t(<English source string>)` so the
 * VS Code l10n bundles (`l10n/bundle.l10n.<locale>.json`) — which key on
 * source strings, NOT abstract identifiers — actually find translations.
 * Posted to the webview right after `webview-ready`.
 */
function getWebviewStrings(): Record<string, string> {
  return {
    'webview.status.disconnected': vscode.l10n.t('Disconnected'),
    'webview.status.connecting': vscode.l10n.t('Connecting…'),
    'webview.status.reconnecting': vscode.l10n.t('Reconnecting…'),
    'webview.status.connected': vscode.l10n.t('Connected'),
    'webview.status.notConnected': vscode.l10n.t('Not connected'),
    'webview.banner.connectionLost': vscode.l10n.t('Connection lost. Trying to reconnect…'),
    'webview.connect.title': vscode.l10n.t('Not connected'),
    'webview.connect.description': vscode.l10n.t(
      'Start the Relay on your My_AI host PC, click "Copy for the VS Code extension" in the Relay popup, then paste the connection string here.',
    ),
    'webview.connect.button': vscode.l10n.t('Paste connection string…'),
    'webview.connect.hint': vscode.l10n.t('Your credentials stay encrypted in VS Code SecretStorage.'),
    'webview.welcome.title': 'My_AI Relay',
    'webview.welcome.text': vscode.l10n.t(
      'Connected to your self-hosted assistant. Type a message to start.',
    ),
    'webview.header.autoAttachTooltip': vscode.l10n.t(
      'Auto-attach the active editor file to every message',
    ),
    'webview.header.autoAttachOn': vscode.l10n.t('Auto-attach: on'),
    'webview.header.autoAttachOff': vscode.l10n.t('Auto-attach: off'),
    'webview.header.clearTooltip': vscode.l10n.t('Clear chat (local view only)'),
    'webview.header.clear': vscode.l10n.t('Clear'),
    'webview.header.reconnect': vscode.l10n.t('New connection'),
    'webview.header.reconnectTooltip': vscode.l10n.t(
      'Paste a new connection string (use this if you restarted the Relay and the token changed)',
    ),
    'webview.input.placeholder': vscode.l10n.t('Type your message…'),
    'webview.input.attachTooltip': vscode.l10n.t('Attach a file or image'),
    'webview.send.stopTooltip': vscode.l10n.t('Stop generation'),
    'webview.code.insert': vscode.l10n.t('Insert'),
    'webview.code.copy': vscode.l10n.t('Copy'),
    'webview.code.inserted': vscode.l10n.t('Inserted!'),
    'webview.code.copied': vscode.l10n.t('Copied!'),
    'webview.attachment.remove': vscode.l10n.t('Remove'),
    'webview.attachment.error': vscode.l10n.t('error'),
  };
}
