import { EventEmitter } from 'events';
import * as path from 'path';
import * as vscode from 'vscode';
import { parseConnectionString } from './connectionString';
import { RelayClient, UploadResult } from './relayClient';
import { DispatchEvent, ToolDispatcher } from './toolDispatcher';
import {
  ConnectionState,
  RelayCredentials,
  HistoryItem,
  IncomingPayload,
  PromptTemplate,
  ToolCall,
  UnlockResult,
} from './types';

const SECRET_KEY = 'myaiRelay.credentials.v1';
const HEALTH_DEAD_BEFORE_DISCONNECT = 3;

export interface ConnectionManagerEvents {
  'state-changed': (state: ConnectionState) => void;
  'message': (payload: IncomingPayload) => void;
  'tool-event': (event: DispatchEvent) => void;
}

export class ConnectionManager extends EventEmitter {
  private context: vscode.ExtensionContext;
  private client: RelayClient | null = null;
  private state: ConnectionState = { kind: 'idle' };
  private healthTimer: NodeJS.Timeout | null = null;
  private healthFailures = 0;
  private lastCreds: RelayCredentials | null = null;
  private dispatcher: ToolDispatcher;
  // Réponses arrêtées par l'utilisateur (Stop, ou Clear pendant la génération).
  private stoppedMessageIds = new Set<string>();

  constructor(context: vscode.ExtensionContext) {
    super();
    this.context = context;
    this.dispatcher = new ToolDispatcher();
    // Forward dispatcher events as 'tool-event' on this emitter so the
    // chat view can update its tool cards.
    this.dispatcher.onEvent((event) => {
      this.emit('tool-event', event);
    });
  }

  getDispatcher(): ToolDispatcher {
    return this.dispatcher;
  }

  getState(): ConnectionState {
    return this.state;
  }

  hasSavedCredentials(): Promise<boolean> {
    return this.context.secrets.get(SECRET_KEY).then((v) => !!v);
  }

  async restoreFromStorage(): Promise<boolean> {
    const stored = await this.context.secrets.get(SECRET_KEY);
    if (!stored) {
      return false;
    }
    let creds: RelayCredentials;
    try {
      creds = JSON.parse(stored) as RelayCredentials;
    } catch {
      await this.context.secrets.delete(SECRET_KEY);
      return false;
    }
    await this.connectWith(creds, { persist: false });
    return true;
  }

  async connectFromString(rawConnectionString: string): Promise<void> {
    const creds = parseConnectionString(rawConnectionString);
    const session = await this.askAccessCode(creds);
    if (session === null) {
      // Cancelled: nothing saved, the current connection (if any) stays.
      return;
    }
    await this.connectWith({ ...creds, session: session || undefined }, { persist: true });
  }

  async disconnect(forget: boolean): Promise<void> {
    this.stopHealthLoop();
    if (this.client) {
      this.client.removeAllListeners();
      this.client.close();
      this.client = null;
    }
    if (forget) {
      await this.context.secrets.delete(SECRET_KEY);
      this.lastCreds = null;
    }
    this.setState({ kind: 'disconnected', reason: forget ? 'Forgotten by user' : 'Disconnected by user' });
  }

  async loadHistory(): Promise<HistoryItem[]> {
    if (!this.client) {
      return [];
    }
    return this.client.loadHistory();
  }

  async loadPrompts(): Promise<PromptTemplate[]> {
    if (!this.client) {
      return [];
    }
    return this.client.loadPrompts();
  }

  async stopGeneration(messageId: string): Promise<void> {
    if (messageId) {
      this.stoppedMessageIds.add(messageId);
    }
    if (!this.client) {
      return;
    }
    await this.client.sendStop(messageId);
  }

  async sendChat(text: string, fileIds: string[] = []): Promise<void> {
    if (!this.client) {
      throw new Error('Not connected');
    }
    await this.client.sendChat(text, fileIds);
  }

  async uploadFile(filename: string, data: Uint8Array): Promise<UploadResult> {
    if (!this.client) {
      throw new Error('Not connected');
    }
    return this.client.uploadFile(filename, data);
  }

  /** Attache/réindexe/détache un fichier ou dossier projet (@codebase) côté host. */
  async sendCodebase(
    action: string, folder: string, workspaceRoot?: string,
  ): Promise<void> {
    if (!this.client) {
      throw new Error('Not connected');
    }
    await this.client.sendCodebase(action, folder, workspaceRoot);
  }

  async resumeIfWaiting(lastMessageId: string): Promise<void> {
    if (!this.client) {
      return;
    }
    await this.client.sendResume(lastMessageId);
  }

  async checkPending(messageId: string): Promise<unknown> {
    if (!this.client) {
      return null;
    }
    return this.client.checkPending(messageId);
  }

  // ────────────────────────────────────────────────────────────────────

  /**
   * Ask for the access code shown under the QR code in the host's Relay
   * panel until the host accepts one. Returns the session it opens, '' when
   * the host predates the access code, null when the user cancels. Throws
   * when no tunnel answers or when too many wrong codes locked the Relay.
   */
  private async askAccessCode(creds: RelayCredentials): Promise<string | null> {
    const cfg = vscode.workspace.getConfiguration('myaiRelay');
    const client = new RelayClient(creds, cfg.get<number>('requestTimeoutSeconds', 15));
    const required = await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Window,
        title: vscode.l10n.t('My_AI Relay: contacting the host…'),
      },
      () => client.accessCodeRequired(),
    );
    if (!required) {
      return '';
    }
    let notice = '';
    for (;;) {
      const input = await vscode.window.showInputBox({
        title: vscode.l10n.t('My_AI Relay — Access code'),
        prompt: notice || vscode.l10n.t(
          'Enter the access code shown under the QR code in the Relay panel of My_AI',
        ),
        placeHolder: '123 456',
        ignoreFocusOut: true,
        validateInput: (value) => (/^[\d\s]*$/.test(value) ? null : vscode.l10n.t('Digits only.')),
      });
      if (input === undefined) {
        return null;
      }
      const code = input.replace(/\D/g, '');
      const result: UnlockResult = code.length === 6
        ? await client.unlock(code)
        : { ok: false, error: 'format' };
      if (result.ok && result.session) {
        return result.session;
      }
      if (result.error === 'locked') {
        throw new Error(vscode.l10n.t(
          'Too many wrong access codes: the Relay now refuses every connection. Restart it on the host PC to get a new connection string and a new code.',
        ));
      }
      if (result.error === 'format') {
        notice = vscode.l10n.t('The access code has 6 digits.');
      } else if (result.remaining === 1) {
        notice = vscode.l10n.t('Wrong access code: 1 try left.');
      } else {
        notice = vscode.l10n.t('Wrong access code: {0} tries left.', result.remaining ?? 0);
      }
    }
  }

  private async connectWith(
    creds: RelayCredentials,
    opts: { persist: boolean },
  ): Promise<void> {
    if (this.client) {
      this.client.removeAllListeners();
      this.client.close();
      this.client = null;
    }
    this.stopHealthLoop();
    this.lastCreds = creds;
    this.setState({ kind: 'connecting' });

    if (opts.persist) {
      await this.context.secrets.store(SECRET_KEY, JSON.stringify(creds));
    }

    const cfg = vscode.workspace.getConfiguration('myaiRelay');
    const requestTimeout = cfg.get<number>('requestTimeoutSeconds', 15);

    const client = new RelayClient(creds, requestTimeout);
    client.setClientHello({
      client_kind: 'vscode',
      workspace_info: buildWorkspaceInfo(),
    });
    this.client = client;
    // Each new session starts with a clean approval slate.
    this.dispatcher.resetApprovals();

    client.on('connecting', (base: string) => {
      this.setState({ kind: 'connecting', baseUrl: base });
    });
    client.on('connected', (base: string) => {
      this.healthFailures = 0;
      this.setState({ kind: 'connected', baseUrl: base });
      this.startHealthLoop();
    });
    client.on('disconnected', (reason: string) => {
      // Client is already trying to reconnect internally; reflect "reconnecting"
      // unless the user requested a hard disconnect.
      const cfgAuto = vscode.workspace.getConfiguration('myaiRelay').get<boolean>('autoReconnect', true);
      if (cfgAuto) {
        this.setState({ kind: 'reconnecting', lastBaseUrl: client.baseUrl ?? undefined });
      } else {
        this.stopHealthLoop();
        this.setState({ kind: 'disconnected', reason });
      }
    });
    client.on('access-denied', () => {
      // The host refused the session (none saved by an older version of the
      // extension): the client stopped, a new connection asks for the code.
      this.stopHealthLoop();
      this.setState({
        kind: 'disconnected',
        reason: vscode.l10n.t(
          'Access code required: click "New connection" and paste the connection string again.',
        ),
      });
    });
    client.on('error', (err: Error) => {
      // eslint-disable-next-line no-console
      console.warn('[my-ai-relay] client error:', err.message);
    });
    client.on('message', (payload: IncomingPayload) => {
      // Tool calls are intercepted here: we never relay raw tool_use
      // messages to the chat UI as if they were content. Only the
      // dispatcher events ('tool-event') and the post-dispatch chunks
      // are surfaced to the user.
      if (payload && payload.type === 'tool_use') {
        this.handleToolUse(payload).catch((err) => {
          // eslint-disable-next-line no-console
          console.error('[my-ai-relay] tool dispatch failed:', err);
        });
        return;
      }
      this.emit('message', payload);
    });

    try {
      await client.start();
    } catch (err) {
      this.setState({ kind: 'disconnected', reason: (err as Error).message });
    }
  }

  private setState(state: ConnectionState): void {
    this.state = state;
    this.emit('state-changed', state);
  }

  private startHealthLoop(): void {
    this.stopHealthLoop();
    const cfg = vscode.workspace.getConfiguration('myaiRelay');
    const intervalSec = cfg.get<number>('healthCheckIntervalSeconds', 10);
    const intervalMs = Math.max(3000, intervalSec * 1000);

    this.healthTimer = setInterval(async () => {
      if (!this.client || !this.lastCreds) {
        return;
      }
      const alive = await this.client.isAnyTunnelAlive();
      if (alive) {
        this.healthFailures = 0;
        return;
      }
      this.healthFailures += 1;
      if (this.healthFailures >= HEALTH_DEAD_BEFORE_DISCONNECT) {
        // All tunnels are gone for several consecutive checks: declare the
        // host's Relay stopped. Keep credentials in storage so the extension
        // can auto-reconnect once the host restarts the Relay (the WS layer
        // is already in its reconnect backoff loop).
        const auto = vscode.workspace
          .getConfiguration('myaiRelay')
          .get<boolean>('autoReconnect', true);
        if (auto) {
          this.setState({
            kind: 'reconnecting',
            lastBaseUrl: this.client.baseUrl ?? undefined,
          });
        } else {
          this.stopHealthLoop();
          if (this.client) {
            this.client.removeAllListeners();
            this.client.close();
            this.client = null;
          }
          this.setState({
            kind: 'disconnected',
            reason: 'Relay host appears offline (tunnels unreachable).',
          });
        }
      }
    }, intervalMs);
  }

  private stopHealthLoop(): void {
    if (this.healthTimer) {
      clearInterval(this.healthTimer);
      this.healthTimer = null;
    }
    this.healthFailures = 0;
  }

  private async handleToolUse(payload: IncomingPayload): Promise<void> {
    const callId = typeof payload.call_id === 'string' ? payload.call_id : '';
    const name = typeof payload.name === 'string' ? payload.name : '';
    const input = (payload.input && typeof payload.input === 'object')
      ? payload.input as Record<string, unknown>
      : {};
    const messageId = typeof payload.message_id === 'string' ? payload.message_id : undefined;

    if (!callId || !name) {
      // eslint-disable-next-line no-console
      console.warn('[my-ai-relay] tool_use ignored: missing call_id/name');
      return;
    }
    // Appel parti avant le Stop : l'hôte n'attend plus son résultat (et une
    // écriture demanderait une approbation après coup).
    if (messageId && this.stoppedMessageIds.has(messageId)) {
      return;
    }

    const call: ToolCall = { call_id: callId, name, input, message_id: messageId };
    const result = await this.dispatcher.dispatch(call);

    if (!this.client) {
      return;
    }
    try {
      await this.client.sendToolResult(result.call_id, result.content, result.is_error);
    } catch (err) {
      // eslint-disable-next-line no-console
      console.warn('[my-ai-relay] sendToolResult failed:', err);
    }
  }
}

/**
 * Build a short workspace summary that the host's agentic loop will
 * include in the system prompt so the LLM knows what it's working in.
 * Capped on the host side as well.
 */
function buildWorkspaceInfo(): string {
  const folders = vscode.workspace.workspaceFolders;
  if (!folders || folders.length === 0) {
    return 'No workspace folder is open in VS Code.';
  }
  const lines: string[] = [];
  for (const folder of folders) {
    const root = folder.uri.fsPath;
    lines.push(`- ${folder.name} (${root})`);
  }
  const editor = vscode.window.activeTextEditor;
  if (editor) {
    const rel = vscode.workspace.asRelativePath(editor.document.uri);
    lines.push(`Active editor: ${rel} (${editor.document.languageId})`);
  }
  const platform = `${process.platform} (${path.sep === '\\' ? 'Windows' : 'POSIX'} path style)`;
  return [
    'Workspace folders:',
    ...lines,
    `Platform: ${platform}`,
  ].join('\n');
}
