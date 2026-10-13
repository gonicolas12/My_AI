/*
 * Protocole d'événements entre le serveur desktop et la fenêtre.
 *
 * Miroir de interfaces/desktop/events.py : les deux fichiers évoluent ensemble.
 * Chaque événement porte type, conversation_id, message_id, seq (croissant sur
 * toute la vie du serveur) et payload.
 */

// ── État de la conversation (GET /api/conversation, ChatService.snapshot) ──

export type Source = 'desktop' | 'mobile';

export interface AttachmentRef {
  path: string;
  name: string;
  type: string;
}

/** Chemin existant cité dans une réponse, montré dans l'Explorateur au clic */
export interface PathLink {
  /** Tel qu'il apparaît dans la réponse */
  text: string;
  path: string;
}

export interface ToolCallView {
  name: string;
  label: string;
  /** Position dans le texte de la réponse au moment de l'appel */
  at?: number;
  ok?: boolean;
  summary?: string;
  sources?: number;
}

export interface MessageView {
  mid: string;
  role: 'user' | 'assistant';
  text: string;
  timestamp: string | null;
  type: string;
  attachments: AttachmentRef[];
  image_path: string | null;
  source?: Source;
  thinking?: string;
  thinking_ms?: number;
  tool_calls?: ToolCallView[];
  documents?: string[];
  file_path?: string;
  interrupted?: boolean;
  error?: boolean;
  duration_ms?: number;
  tokens_per_s?: number;
  /** Note de 1 à 5 étoiles (RLHF), figée une fois donnée */
  rating?: number;
  /** Chemins existants cités (réponses seulement), calculés par le serveur */
  paths?: PathLink[];
}

export type TurnKind = 'chat' | 'file' | 'image';

export interface ActiveTurnView {
  request_id: string;
  mid: string;
  kind: TurnKind;
  source: Source;
  reasoning: boolean;
  text: string;
  thinking: string;
  tools: ToolCallView[];
  documents: string[];
  status: string;
  filename: string | null;
  started_at: string;
}

export interface QueueItem {
  request_id: string;
  source: Source;
  text: string;
}

export type AttachmentStatus = 'loading' | 'ready' | 'error';

export interface AttachmentView {
  id: string;
  path: string;
  name: string;
  type: string;
  status: AttachmentStatus;
}

export interface ConfirmView {
  confirm_id: string;
  kind: 'delete_file';
  path: string;
  name: string;
}

export interface ConversationSnapshot {
  conversation_id: string | null;
  name: string | null;
  seq: number;
  messages: MessageView[];
  branches: Record<string, { count: number; current: number }>;
  active: ActiveTurnView | null;
  queue: QueueItem[];
  attachments: AttachmentView[];
  confirm: ConfirmView | null;
  busy: boolean;
}

export interface SessionSummary {
  id: string;
  name: string;
  last_modified: string | null;
  message_count: number;
  current: boolean;
}

// ── Application ────────────────────────────────────────────────────────────

export type EngineState = 'starting' | 'onboarding' | 'ready' | 'error';

export interface EngineStatus {
  state: EngineState;
  step: string;
  label: string;
  detail: string;
  error: string | null;
  ollama: boolean;
  placement: string | null;
}

export type NotificationLevel = 'info' | 'success' | 'warning' | 'error';

export interface NotificationPayload {
  level: NotificationLevel;
  message: string;
}

export interface RelayStatus {
  running: boolean;
  port: number | null;
  clients: number;
  tunnels: Record<string, string>;
  url: string | null;
  local_url: string | null;
}

export type VoiceInputState = 'idle' | 'recording' | 'transcribing' | 'error';

export type VoiceOutputState = 'speaking' | 'idle' | 'error';

export interface SchedulerResult {
  task_id: string | null;
  name: string;
  status: string;
  status_text: string;
  summary: string;
  output_file: string | null;
  finished_at: string | null;
  os_toast_shown: boolean;
}

// ── Charges utiles des événements ─────────────────────────────────────────

export interface EventPayloads {
  'engine.status': EngineStatus;
  notification: NotificationPayload;
  'relay.status': RelayStatus;
  'scheduler.result': SchedulerResult;
  'sessions.changed': Record<string, never>;
  'files.dropped': { paths: string[] };
  'folders.progress': { path: string; name: string; verb: string; done: number; total: number };
  'folders.changed': { path: string | null; ok: boolean };
  'voice.input': { state: VoiceInputState; message: string };
  'voice.transcript': { text: string };
  'voice.output': { state: VoiceOutputState; key: string | null; message: string };
  'conversation.loaded': {
    reason: 'new' | 'cleared' | 'loaded' | 'restored' | 'edited' | 'navigated';
    snapshot: ConversationSnapshot;
  };
  'queue.updated': { items: QueueItem[] };
  'message.user': {
    mid: string;
    request_id: string;
    text: string;
    source: Source;
    timestamp: string;
    attachments: AttachmentRef[];
    image_path: string | null;
  };
  'message.rated': { mid: string; rating: number };
  'assistant.start': {
    mid: string;
    request_id: string;
    kind: TurnKind;
    reasoning: boolean;
    filename: string | null;
  };
  'assistant.token': { text: string };
  'assistant.sync': { text: string };
  'assistant.thinking': { text: string };
  'assistant.thinking_done': { duration_ms: number };
  'assistant.done': {
    mid: string;
    text: string;
    duration_ms: number;
    tokens_per_s: number | null;
    paths?: PathLink[];
  };
  'assistant.interrupted': { mid: string | null; text: string; paths?: PathLink[] };
  'assistant.error': { mid: string | null; message: string };
  'tool.call': { name: string; label: string; args: Record<string, unknown>; at: number };
  'tool.result': { name: string; ok: boolean; summary: string; sources: number };
  'confirm.request': ConfirmView;
  'confirm.closed': { confirm_id: string; accepted: boolean };
  'document.created': { path: string; name: string };
  'file.created': { path: string; name: string };
  'image.progress': { message: string; fraction: number | null };
  'image.created': { path: string; name: string };
  'attachment.added': AttachmentView;
  'attachment.ready': { id: string };
  'attachment.failed': { id: string; message: string };
  'attachment.removed': { id: string };
}

export type EventType = keyof EventPayloads;

export interface ServerEvent<T extends EventType = EventType> {
  type: T;
  conversation_id: string | null;
  message_id: string | null;
  seq: number;
  payload: EventPayloads[T];
}

/** Événement de la page Agents (préfixe « agents. », repris d'AgentRelayService) */
export interface AgentServerEvent {
  type: `agents.${string}`;
  conversation_id: string | null;
  message_id: string | null;
  seq: number;
  payload: Record<string, unknown>;
}

export type AnyServerEvent = { [T in EventType]: ServerEvent<T> }[EventType] | AgentServerEvent;

/** Messages de contrôle, hors protocole d'événements */
export interface HelloMessage {
  type: 'hello';
  resumed: boolean;
}

export interface ReplyMessage {
  type: 'reply';
  ref: string | null;
  ok: boolean;
  data?: Record<string, unknown>;
  error?: string;
}

// ── Messages de la fenêtre vers le serveur ────────────────────────────────

export type ClientMessage =
  | {
      type: 'chat.send';
      text: string;
      attachment_ids?: string[] | null;
      edit_mid?: string | null;
      regenerate?: boolean;
    }
  | { type: 'chat.stop' }
  | { type: 'chat.cancel'; request_id: string }
  | { type: 'confirm.response'; confirm_id: string; accepted: boolean }
  | { type: 'ping' };

/** Événements qui modifient l'état du chat (CHAT_EVENT_TYPES de events.py) */
const CHAT_PREFIXES = new Set([
  'conversation',
  'queue',
  'message',
  'assistant',
  'tool',
  'confirm',
  'document',
  'file',
  'image',
  'attachment',
]);

export function isChatEvent(type: string): boolean {
  return CHAT_PREFIXES.has(type.split('.')[0] ?? '');
}

export function isAgentEvent(event: AnyServerEvent): event is AgentServerEvent {
  return event.type.startsWith('agents.');
}
