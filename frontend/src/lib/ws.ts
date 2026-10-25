/*
 * Connexion WebSocket au serveur local : événements, réponses aux messages de
 * la fenêtre, reconnexion.
 *
 * À la reconnexion, la fenêtre redonne le seq du dernier événement reçu : le
 * serveur rejoue ce qu'elle a manqué (« hello » avec resumed=true), ou lui
 * demande de relire l'état complet s'il ne les garde plus (resumed=false).
 */

import { t } from '../i18n';
import type { AnyServerEvent, ClientMessage, HelloMessage, ReplyMessage } from './events';

export type ConnectionState = 'connecting' | 'open' | 'reconnecting';

export interface EventSocketHandlers {
  /** Événement reçu, dans l'ordre du serveur */
  onEvent: (event: AnyServerEvent) => void;
  /** Connexion (ré)ouverte ; resync vaut true s'il faut relire l'état complet */
  onHello: (resync: boolean) => void;
  onState: (state: ConnectionState) => void;
}

/** Problème de connexion ; sent vaut false si le message n'est jamais parti */
export class SocketError extends Error {
  readonly sent: boolean;

  constructor(message: string, sent: boolean) {
    super(message);
    this.name = 'SocketError';
    this.sent = sent;
  }
}

/** Action refusée par le serveur (réponse en cours, message vide…) */
export class ReplyError extends Error {
  constructor(message: string) {
    super(message);
    this.name = 'ReplyError';
  }
}

interface PendingReply {
  resolve: (data: Record<string, unknown>) => void;
  reject: (error: Error) => void;
  timer: ReturnType<typeof setTimeout>;
}

const RETRY_DELAYS = [250, 500, 1000, 2000];
const REPLY_TIMEOUT = 30_000;

export class EventSocket {
  private ws: WebSocket | null = null;
  private lastSeq: number | null = null;
  private attempts = 0;
  private everConnected = false;
  private stopped = false;
  private retryTimer: ReturnType<typeof setTimeout> | null = null;
  private nextId = 1;
  private readonly pending = new Map<string, PendingReply>();

  private readonly url: () => string;
  private readonly handlers: EventSocketHandlers;

  constructor(url: () => string, handlers: EventSocketHandlers) {
    this.url = url;
    this.handlers = handlers;
  }

  /** Seq du dernier événement reçu */
  get seq(): number | null {
    return this.lastSeq;
  }

  start(): void {
    this.stopped = false;
    this.open();
  }

  stop(): void {
    this.stopped = true;
    if (this.retryTimer) clearTimeout(this.retryTimer);
    this.ws?.close();
    this.ws = null;
    this.failPending(t('connection.closed'));
  }

  /** Envoie un message ; la promesse rend les données de la réponse du serveur. */
  send(message: ClientMessage): Promise<Record<string, unknown>> {
    const ws = this.ws;
    if (!ws || ws.readyState !== WebSocket.OPEN) {
      return Promise.reject(new SocketError(t('connection.pending'), false));
    }
    const id = String(this.nextId++);
    return new Promise((resolve, reject) => {
      const timer = setTimeout(() => {
        this.pending.delete(id);
        reject(new SocketError(t('connection.noResponse'), true));
      }, REPLY_TIMEOUT);
      this.pending.set(id, { resolve, reject, timer });
      ws.send(JSON.stringify({ ...message, id }));
    });
  }

  private open(): void {
    this.handlers.onState(this.everConnected ? 'reconnecting' : 'connecting');
    const params = new URLSearchParams();
    let url = this.url();
    if (this.lastSeq !== null) params.set('since', String(this.lastSeq));
    const query = params.toString();
    if (query) url += (url.includes('?') ? '&' : '?') + query;

    let ws: WebSocket;
    try {
      ws = new WebSocket(url);
    } catch {
      this.scheduleRetry();
      return;
    }
    this.ws = ws;
    ws.onmessage = (message: MessageEvent<string>) => this.receive(message.data);
    ws.onclose = () => {
      if (this.ws === ws) this.ws = null;
      this.failPending(t('connection.lost'));
      if (!this.stopped) this.scheduleRetry();
    };
  }

  private scheduleRetry(): void {
    if (this.stopped) return;
    this.handlers.onState(this.everConnected ? 'reconnecting' : 'connecting');
    const delay = RETRY_DELAYS[Math.min(this.attempts, RETRY_DELAYS.length - 1)] ?? 2000;
    this.attempts += 1;
    this.retryTimer = setTimeout(() => this.open(), delay);
  }

  private receive(raw: string): void {
    let data: AnyServerEvent | HelloMessage | ReplyMessage;
    try {
      data = JSON.parse(raw) as AnyServerEvent | HelloMessage | ReplyMessage;
    } catch {
      return;
    }
    if (data.type === 'hello') {
      const hello = data;
      const resync = !this.everConnected || !hello.resumed;
      this.everConnected = true;
      this.attempts = 0;
      this.handlers.onState('open');
      this.handlers.onHello(resync);
      return;
    }
    if (data.type === 'reply') {
      const reply = data;
      const waiting = reply.ref ? this.pending.get(reply.ref) : undefined;
      if (!waiting || !reply.ref) return;
      this.pending.delete(reply.ref);
      clearTimeout(waiting.timer);
      if (reply.ok) waiting.resolve(reply.data ?? {});
      else waiting.reject(new ReplyError(reply.error ?? t('connection.refused')));
      return;
    }
    const event = data;
    if (typeof event.seq !== 'number') return;
    // Rejeu après reconnexion : rien en double
    if (this.lastSeq !== null && event.seq <= this.lastSeq) return;
    this.lastSeq = event.seq;
    this.handlers.onEvent(event);
  }

  private failPending(message: string): void {
    for (const [id, waiting] of this.pending) {
      clearTimeout(waiting.timer);
      waiting.reject(new SocketError(message, true));
      this.pending.delete(id);
    }
  }
}
