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

/** Tunnel vu de ce PC : pas encore vérifié, joignable (dans le QR code) ou muet */
export type TunnelState = 'checking' | 'ok' | 'dead';

export interface RelayStatus {
  running: boolean;
  port: number | null;
  clients: number;
  tunnels: Record<string, string>;
  tunnel_states?: Record<string, TunnelState>;
  /** Page de routage (QR code) : tunnels joignables seulement ; null tant qu'aucun ne répond */
  url: string | null;
  local_url: string | null;
  /** Code d'accès (sous le QR code) : demandé au téléphone et à VS Code, en plus du lien */
  access_code?: string | null;
  /** Codes d'accès erronés saisis depuis le démarrage du Relay */
  access_failures?: number;
  /** Trop de codes erronés : plus aucun n'est accepté jusqu'au redémarrage */
  access_locked?: boolean;
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

/** Mesure du moniteur de ressources (ResourceMonitor de Tk) ; CPU et RAM d'Ollama seul */
export interface ResourceMetrics {
  cpu_percent: number;
  ram_used_mb: number;
  ram_total_mb: number;
  ram_percent: number;
  gpu_available: boolean;
  gpu_percent: number;
  gpu_mem_used_mb: number;
  gpu_mem_total_mb: number;
  /** Durée du dernier agent */
  inference_ms: number;
  /** Tokens/s du dernier agent */
  tokens_per_sec: number;
}

// ── Charges utiles des événements ─────────────────────────────────────────

export interface EventPayloads {
  'engine.status': EngineStatus;
  notification: NotificationPayload;
  'relay.status': RelayStatus;
  /** Langue de l'interface changée (Réglages, assistant) : la fenêtre la suit */
  'i18n.language': { language: string };
  'scheduler.result': SchedulerResult;
  /** La liste des tâches planifiées a changé : la page la relit */
  'scheduler.changed': Record<string, never>;
  /** Mesure du moniteur ; inferences : fins d'agents relevées (un point de tokens/s chacune) */
  'resources.sample': { metrics: ResourceMetrics; inferences: number };
  'sessions.changed': Record<string, never>;
  'files.dropped': { paths: string[] };
  'folders.progress': { path: string; name: string; verb: string; done: number; total: number };
  'folders.changed': { path: string | null; ok: boolean };
  'models.progress': { fraction: number; status: string };
  'models.log': { line: string };
  'models.done': {
    action: 'pull' | 'apply' | 'install';
    name: string;
    ok: boolean;
    message: string;
  };
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

// ── Page Agents (interfaces/desktop/agents.py) ────────────────────────────

/** Agent de la grille (AgentRelayService.list_agents) */
export interface AgentInfo {
  key: string;
  /** Émoji de Tk (🐍, 🔍…) ; 🧩 pour un agent personnalisé */
  icon: string;
  name: string;
  /** Description courte (rédigée par le modèle pour un agent personnalisé) */
  desc: string;
  color: string;
  custom?: boolean;
  /** Rôle saisi à la création d'un agent personnalisé */
  full_desc?: string;
}

export interface AgentsList {
  builtin: AgentInfo[];
  custom: AgentInfo[];
  default_model: string;
}

/** Statut d'un nœud du canvas (WorkflowCanvas.STATUS_META de Tk) */
export type NodeStatus = 'idle' | 'running' | 'done' | 'error';

export type RunStatus = 'running' | 'done' | 'error' | 'interrupted';

export type RunKind = 'agent' | 'workflow' | 'debate';

/** Origine d'un fil : la page, le téléphone (Relay) ou une tâche planifiée (D37) */
export type RunOrigin = 'desktop' | 'mobile' | 'scheduled';

/** Section d'un nœud, ou « deb_N » pour un tour de débat */
export type SectionId = number | string;

/** Nœud du workflow d'un fil ; identifiant entier (canvas), ou texte (téléphone, tâche planifiée) */
export interface RunNode {
  id: SectionId;
  agent_type: string;
  name: string;
  color: string;
  icon?: string;
  x?: number;
  y?: number;
}

export interface RunSection {
  id: SectionId;
  title: string;
  color: string;
  agent_type: string | null;
  text: string;
  status: 'running' | 'done' | 'error';
  started_at: string | null;
  finished_at: string | null;
  /** Durée de l'agent (ms) et ses tokens/s (relevé de fin de flux d'Ollama) */
  inference_ms?: number | null;
  tokens_per_sec?: number | null;
}

/** Débat : proposant, opposant, nombre de tours */
export interface RunDebate {
  agent_a: string;
  agent_b: string;
  rounds: number;
}

/** Tâche planifiée d'un fil, et son rapport une fois écrit */
export interface RunSchedule {
  task_id: string | null;
  name: string | null;
  output_file: string | null;
}

export interface RunPlan {
  mode: string;
  /** Étapes du plan : identifiants des nœuds, une étape à plusieurs = en parallèle */
  steps: SectionId[][];
  isolated: SectionId[];
}

export interface RunAttachment {
  path: string;
  name: string;
  type: string;
}

/** Fil d'exécution complet (GET /api/agents/runs/{id}) */
export interface RunView {
  id: string;
  kind: RunKind;
  origin: RunOrigin;
  title: string;
  task: string;
  attachments: RunAttachment[];
  /** Code joint à la tâche, gardé pour le diff des sorties qui le modifient */
  sources: { name: string; text: string }[];
  nodes: RunNode[];
  connections: { from: SectionId; to: SectionId }[];
  plan: RunPlan;
  debate: RunDebate | null;
  schedule: RunSchedule | null;
  mode: string | null;
  status: RunStatus;
  status_text: string;
  error: string | null;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  sections: RunSection[];
  node_status: Record<string, NodeStatus>;
}

/** Ligne de la liste des fils */
export interface RunSummary {
  id: string;
  kind: RunKind;
  origin: RunOrigin;
  title: string;
  task: string;
  status: RunStatus;
  status_text: string;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  agent_type: string | null;
  color: string | null;
  agents: number;
  /** Tâche planifiée dont le fil est une exécution */
  schedule_task_id: string | null;
}

export interface AgentEventPayloads {
  'agents.run_created': { run: RunView };
  'agents.agent_exec_start': { exec_id: string; mode: string };
  'agents.agent_debate_topic': { exec_id: string; topic: string };
  'agents.agent_section_start': {
    exec_id: string;
    section_id: SectionId;
    title: string;
    color: string;
  };
  /** Suite du texte d'une section ; offset : longueur du texte avant elle */
  'agents.agent_section_delta': {
    exec_id: string;
    section_id: SectionId;
    text: string;
    offset: number;
  };
  /** Texte entier d'une section, quand il ne prolonge pas le précédent */
  'agents.agent_section_text': { exec_id: string; section_id: SectionId; text: string };
  'agents.agent_section_end': {
    exec_id: string;
    section_id: SectionId;
    success: boolean;
    inference_ms?: number | null;
    tokens_per_sec?: number | null;
  };
  'agents.agent_node_status': { exec_id: string; node_id: SectionId; status: NodeStatus };
  'agents.agent_exec_end': {
    exec_id: string;
    success: boolean;
    interrupted: boolean;
    status_text: string;
  };
  'agents.agent_exec_error': { exec_id: string; message: string };
  'agents.runs_changed': Record<string, never>;
  'agents.list_changed': Record<string, never>;
}

export type AgentEventType = keyof AgentEventPayloads;

/** Événement de la page Agents (préfixe « agents. ») */
export interface AgentServerEvent<T extends AgentEventType = AgentEventType> {
  type: T;
  conversation_id: string | null;
  message_id: string | null;
  seq: number;
  payload: AgentEventPayloads[T];
}

export type AnyAgentEvent = { [T in AgentEventType]: AgentServerEvent<T> }[AgentEventType];

export type AnyServerEvent = { [T in EventType]: ServerEvent<T> }[EventType] | AnyAgentEvent;

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

export function isAgentEvent(event: AnyServerEvent): event is AnyAgentEvent {
  return event.type.startsWith('agents.');
}
