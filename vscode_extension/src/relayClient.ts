import { EventEmitter } from 'events';
import WebSocket from 'ws';
import {
  aesGcmEncryptBytes,
  decryptEnvelope,
  encryptEnvelope,
  importAesGcmKey,
} from './crypto';
import { HistoryItem, IncomingPayload, PromptTemplate, RelayCredentials } from './types';

const RECONNECT_BASE_MS = 2000;
const RECONNECT_MAX_MS = 30000;
// Keepalive court (15s) car certains tunnels publics (serveo, localhost.run
// via mobile data) coupent les WebSockets idle bien avant les 25s habituels
// de cloudflared. Un ping plus fréquent garde la connexion vivante au prix
// d'un petit overhead réseau.
const KEEPALIVE_MS = 15000;

export interface UploadResult {
  fileId: string;
  filename: string;
  isImage: boolean;
  size: number;
}

interface ChatPayload {
  type: 'chat';
  message: string;
  file_ids?: string[];
}

export interface ClientHelloPayload {
  client_kind: 'vscode';
  workspace_info: string;
}

export class RelayClient extends EventEmitter {
  private creds: RelayCredentials;
  private cryptoKey: CryptoKey | null = null;
  private ws: WebSocket | null = null;
  private currentBaseUrl: string | null = null;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private reconnectAttempts = 0;
  private keepaliveTimer: NodeJS.Timeout | null = null;
  private requestTimeoutMs: number;
  private closed = false;
  private clientHello: ClientHelloPayload | null = null;

  constructor(creds: RelayCredentials, requestTimeoutSeconds: number) {
    super();
    this.creds = creds;
    this.requestTimeoutMs = Math.max(2000, requestTimeoutSeconds * 1000);
  }

  /**
   * Sets the payload sent right after the WebSocket opens to register
   * this client as a VS Code agentic client. If null/unset, the relay
   * treats the connection as a generic mobile client (legacy flow).
   */
  setClientHello(payload: ClientHelloPayload | null): void {
    this.clientHello = payload;
  }

  get baseUrl(): string | null {
    return this.currentBaseUrl;
  }

  get isOpen(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  async start(): Promise<void> {
    this.cryptoKey = await importAesGcmKey(this.creds.keyB64u);
    await this.connectFirstAlive();
  }

  close(): void {
    this.closed = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.keepaliveTimer) {
      clearInterval(this.keepaliveTimer);
      this.keepaliveTimer = null;
    }
    if (this.ws) {
      try {
        this.ws.close();
      } catch {
        /* ignore */
      }
      this.ws = null;
    }
  }

  /**
   * Probe each tunnel URL via /api/health and return the first that answers
   * within the request timeout. Throws if none responds.
   */
  async probeAliveTunnel(): Promise<string> {
    const errors: string[] = [];
    for (const base of this.creds.urls) {
      try {
        const ok = await this.fetchJson(`${base}/api/health`);
        if (ok && typeof ok === 'object' && (ok as { status?: string }).status === 'ok') {
          return base;
        }
        errors.push(`${base}: unexpected response`);
      } catch (err) {
        errors.push(`${base}: ${(err as Error).message}`);
      }
    }
    throw new Error(`No tunnel reachable. Tried:\n${errors.join('\n')}`);
  }

  /**
   * Lightweight health probe used by the connection manager polling loop.
   * Returns true if at least one tunnel responds. Does NOT change any state.
   */
  async isAnyTunnelAlive(): Promise<boolean> {
    for (const base of this.creds.urls) {
      try {
        const ok = await this.fetchJson(`${base}/api/health`, 5000);
        if (ok && typeof ok === 'object' && (ok as { status?: string }).status === 'ok') {
          return true;
        }
      } catch {
        /* try next */
      }
    }
    return false;
  }

  async loadHistory(): Promise<HistoryItem[]> {
    if (!this.cryptoKey || !this.currentBaseUrl) {
      throw new Error('Relay not connected');
    }
    const url = `${this.currentBaseUrl}/api/history?token=${encodeURIComponent(this.creds.token)}`;
    const wrapper = await this.fetchJson(url);
    const decrypted = (await decryptEnvelope(this.cryptoKey, wrapper)) as { history?: HistoryItem[] };
    return Array.isArray(decrypted?.history) ? decrypted.history : [];
  }

  async loadPrompts(): Promise<PromptTemplate[]> {
    if (!this.cryptoKey || !this.currentBaseUrl) {
      throw new Error('Relay not connected');
    }
    const url = `${this.currentBaseUrl}/api/prompts?token=${encodeURIComponent(this.creds.token)}`;
    const wrapper = await this.fetchJson(url);
    const decrypted = (await decryptEnvelope(this.cryptoKey, wrapper)) as { prompts?: PromptTemplate[] };
    return Array.isArray(decrypted?.prompts) ? decrypted.prompts : [];
  }

  async checkPending(messageId: string): Promise<{
    pending: boolean;
    final?: boolean;
    message?: string;
    timestamp?: string;
  } | null> {
    if (!this.cryptoKey || !this.currentBaseUrl) {
      return null;
    }
    const url = `${this.currentBaseUrl}/api/pending?token=${encodeURIComponent(this.creds.token)}&message_id=${encodeURIComponent(messageId)}`;
    try {
      const wrapper = await this.fetchJson(url);
      return (await decryptEnvelope(this.cryptoKey, wrapper)) as {
        pending: boolean;
        final?: boolean;
        message?: string;
        timestamp?: string;
      };
    } catch {
      return null;
    }
  }

  async uploadFile(filename: string, data: Uint8Array): Promise<UploadResult> {
    if (!this.cryptoKey || !this.currentBaseUrl) {
      throw new Error('Relay not connected');
    }
    const fnameBytes = new TextEncoder().encode(filename);
    if (fnameBytes.length === 0 || fnameBytes.length > 256) {
      throw new Error('filename length must be 1..256 bytes');
    }
    const header = new Uint8Array(4 + 2 + fnameBytes.length);
    header[0] = 0x4d; header[1] = 0x59; header[2] = 0x41; header[3] = 0x49; // "MYAI"
    header[4] = (fnameBytes.length >> 8) & 0xff;
    header[5] = fnameBytes.length & 0xff;
    header.set(fnameBytes, 6);

    const plain = new Uint8Array(header.length + data.length);
    plain.set(header, 0);
    plain.set(data, header.length);

    const wire = await aesGcmEncryptBytes(this.cryptoKey, plain);

    const boundary = `----myaiBoundary${Date.now().toString(16)}`;
    const preamble = Buffer.from(
      `--${boundary}\r\n` +
        `Content-Disposition: form-data; name="file"; filename="enc.bin"\r\n` +
        `Content-Type: application/octet-stream\r\n\r\n`,
      'utf-8',
    );
    const epilogue = Buffer.from(`\r\n--${boundary}--\r\n`, 'utf-8');
    const body = Buffer.concat([preamble, Buffer.from(wire), epilogue]);

    const url = `${this.currentBaseUrl}/api/upload?token=${encodeURIComponent(this.creds.token)}`;
    const res = await this.fetchRaw(url, {
      method: 'POST',
      headers: {
        'content-type': `multipart/form-data; boundary=${boundary}`,
        'content-length': String(body.byteLength),
      },
      body,
    });

    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try {
        const err = (await res.json()) as { detail?: string };
        if (err?.detail) {
          detail = err.detail;
        }
      } catch {
        /* ignore */
      }
      throw new Error(detail);
    }

    const wrapper = (await res.json()) as unknown;
    const resp = (await decryptEnvelope(this.cryptoKey, wrapper)) as {
      file_id: string;
      filename: string;
      is_image: boolean;
      size: number;
    };
    return {
      fileId: resp.file_id,
      filename: resp.filename,
      isImage: !!resp.is_image,
      size: resp.size,
    };
  }

  async sendChat(text: string, fileIds: string[] = []): Promise<void> {
    const payload: ChatPayload = { type: 'chat', message: text };
    if (fileIds.length > 0) {
      payload.file_ids = fileIds;
    }
    await this.sendEncrypted(payload);
  }

  async sendResume(lastMessageId: string): Promise<void> {
    await this.sendEncrypted({ type: 'resume', last_message_id: lastMessageId });
  }

  /**
   * Attache / réindexe / détache un dossier projet (@codebase) côté host.
   * `action` ∈ { codebase_attach, codebase_reindex, codebase_detach, codebase_status }.
   * Les résultats arrivent via des messages 'codebase_result' / 'codebase_progress'.
   */
  async sendCodebase(
    action: string, folder: string, workspaceRoot?: string,
  ): Promise<void> {
    await this.sendEncrypted({ type: action, folder, workspace_root: workspaceRoot });
  }

  /** Demande au host d'arrêter la génération en cours (LLM + appels d'outils). */
  async sendStop(messageId: string): Promise<void> {
    await this.sendEncrypted({ type: 'stop_generation', message_id: messageId });
  }

  /**
   * Reply to a `tool_use` request from the host's agentic loop with the
   * result of running the tool inside the VS Code workspace.
   */
  async sendToolResult(
    callId: string,
    content: string,
    isError: boolean,
  ): Promise<void> {
    await this.sendEncrypted({
      type: 'tool_result',
      call_id: callId,
      content,
      is_error: isError,
    });
  }

  // ────────────────────────────────────────────────────────────────────
  // Internals
  // ────────────────────────────────────────────────────────────────────

  private async connectFirstAlive(): Promise<void> {
    if (this.closed) {
      return;
    }
    let base: string;
    try {
      base = await this.probeAliveTunnel();
    } catch (err) {
      this.emit('disconnected', (err as Error).message);
      this.scheduleReconnect();
      return;
    }
    this.currentBaseUrl = base;
    this.openWebSocket(base);
  }

  private openWebSocket(base: string): void {
    const wsUrl = base.replace(/^http/i, 'ws') + `/ws?token=${encodeURIComponent(this.creds.token)}`;
    this.emit('connecting', base);

    let ws: WebSocket;
    try {
      ws = new WebSocket(wsUrl, { handshakeTimeout: this.requestTimeoutMs });
    } catch (err) {
      this.emit('disconnected', (err as Error).message);
      this.scheduleReconnect();
      return;
    }
    this.ws = ws;

    ws.on('open', () => {
      this.reconnectAttempts = 0;
      this.emit('connected', base);
      this.startKeepalive();
      // Identify the client as VS Code if a client_hello was registered.
      // Mobile clients leave this null → server treats them as legacy.
      if (this.clientHello) {
        this.sendEncrypted({
          type: 'client_hello',
          ...this.clientHello,
        }).catch((err) => {
          // eslint-disable-next-line no-console
          console.warn('[RelayClient] client_hello failed:', err);
        });
      }
    });

    ws.on('message', (data) => {
      this.handleWsMessage(data).catch((err) => {
        // eslint-disable-next-line no-console
        console.error('[RelayClient] message handling failed:', err);
      });
    });

    ws.on('close', (code, reason) => {
      this.stopKeepalive();
      this.ws = null;
      this.emit('disconnected', `ws closed (${code}) ${reason?.toString() ?? ''}`.trim());
      this.scheduleReconnect();
    });

    ws.on('error', (err) => {
      this.emit('error', err);
    });
  }

  private async handleWsMessage(data: WebSocket.RawData): Promise<void> {
    if (!this.cryptoKey) {
      return;
    }
    let raw: string;
    if (typeof data === 'string') {
      raw = data;
    } else if (Buffer.isBuffer(data)) {
      raw = data.toString('utf-8');
    } else {
      raw = Buffer.concat(data as Buffer[]).toString('utf-8');
    }
    let wrapper: unknown;
    try {
      wrapper = JSON.parse(raw);
    } catch {
      return;
    }
    let payload: IncomingPayload;
    try {
      payload = (await decryptEnvelope(this.cryptoKey, wrapper)) as IncomingPayload;
    } catch (err) {
      this.emit('error', new Error(`E2EE decrypt failed: ${(err as Error).message}`));
      return;
    }
    this.emit('message', payload);
  }

  private async sendEncrypted(obj: unknown): Promise<void> {
    if (!this.cryptoKey || !this.ws || this.ws.readyState !== WebSocket.OPEN) {
      throw new Error('WebSocket not open');
    }
    const wrapper = await encryptEnvelope(this.cryptoKey, obj);
    this.ws.send(JSON.stringify(wrapper));
  }

  private startKeepalive(): void {
    this.stopKeepalive();
    this.keepaliveTimer = setInterval(() => {
      if (this.isOpen) {
        this.sendEncrypted({ type: 'ping' }).catch((err) => {
          // Un échec de ping est suspect : soit le WS est mort sans
          // émettre 'close', soit la couche E2EE est cassée. Logger
          // pour diagnostic, et fermer le WS pour déclencher le
          // reconnect (sinon on reste bloqué sur un WS zombi).
          // eslint-disable-next-line no-console
          console.warn('[RelayClient] keepalive ping failed:', err);
          if (this.ws) {
            try {
              this.ws.close();
            } catch {
              /* ignore */
            }
          }
        });
      }
    }, KEEPALIVE_MS);
  }

  private stopKeepalive(): void {
    if (this.keepaliveTimer) {
      clearInterval(this.keepaliveTimer);
      this.keepaliveTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.closed || this.reconnectTimer) {
      return;
    }
    this.reconnectAttempts += 1;
    const delay = Math.min(
      RECONNECT_BASE_MS * Math.pow(1.5, this.reconnectAttempts - 1),
      RECONNECT_MAX_MS,
    );
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connectFirstAlive().catch(() => {
        /* re-scheduled internally */
      });
    }, delay);
  }

  private async fetchJson(url: string, timeoutMs?: number): Promise<unknown> {
    const res = await this.fetchRaw(url, undefined, timeoutMs);
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
  }

  private async fetchRaw(
    url: string,
    init?: { method?: string; headers?: Record<string, string>; body?: Buffer | Uint8Array | string },
    timeoutMs?: number,
  ): Promise<Response> {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), timeoutMs ?? this.requestTimeoutMs);
    try {
      const res = await fetch(url, {
        method: init?.method ?? 'GET',
        headers: init?.headers,
        body: init?.body as BodyInit | undefined,
        signal: controller.signal,
      });
      return res;
    } finally {
      clearTimeout(timeout);
    }
  }
}
