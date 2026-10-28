export interface RelayCredentials {
  urls: string[];
  token: string;
  keyB64u: string;
  // Session opened with the access code shown under the host's QR code
  // (POST /api/unlock). Never part of the connection string: a leaked string
  // alone doesn't connect.
  session?: string;
}

// Answer of POST /api/unlock (RelayServer.unlock on the host).
export interface UnlockResult {
  ok: boolean;
  session?: string;
  error?: 'format' | 'wrong' | 'locked';
  remaining?: number;
}

export type ConnectionState =
  | { kind: 'idle' }
  | { kind: 'connecting'; baseUrl?: string }
  | { kind: 'connected'; baseUrl: string }
  | { kind: 'reconnecting'; lastBaseUrl?: string }
  | { kind: 'disconnected'; reason: string };

export interface IncomingPayload {
  type:
    | 'response'
    | 'chunk'
    | 'ack'
    | 'pong'
    | 'resume_empty'
    | 'hello_ack'
    | 'tool_use'
    | 'tool_approval'
    | 'language'
    | 'code_snapshot'
    | 'code_state'
    | 'code_user'
    | 'code_cleared'
    | 'code_stop'
    | string;
  message?: string;
  message_id?: string;
  text?: string;
  timestamp?: string;
  resumed?: boolean;
  broadcast?: boolean;
  final?: boolean;
  // Streaming par segment (mode VS Code agentique) : un segment = une
  // passe LLM entre deux exécutions d'outils. Le client crée une bulle
  // séparée par segment pour intercaler les cartes d'outils dans le bon
  // ordre.
  segment_index?: number;
  // response: done | stopped | error (hosts with the Code conversation)
  status?: string;
  // response: time the reply took, shown under it
  duration_ms?: number;
  // tool_use
  call_id?: string;
  name?: string;
  input?: Record<string, unknown>;
  // Where the message comes from: VS Code, My_AI on the PC, or the phone
  origin?: CodeOrigin;
  // tool_approval
  decision?: string;
  // hello_ack
  server?: string;
  client_kind?: string;
  agentic_enabled?: boolean;
  // hello_ack: the host shares this conversation with its Code page and the phone
  code?: boolean;
  // hello_ack, language: My_AI's language
  language?: string;
  // code_snapshot, code_state
  state?: CodeState;
  messages?: CodeMessage[];
  // code_user, ack
  attachments?: string[];
}

// =============================================================================
// Code conversation — see relay/code_hub.py on the host. The same conversation
// shows in VS Code, on the Code page of My_AI on the PC and on the phone.
// =============================================================================

export type CodeOrigin = 'vscode' | 'desktop' | 'mobile';

export interface CodeState {
  vscode: boolean;
  workspace: string | null;
  busy: boolean;
  message_id: string | null;
  origin: CodeOrigin | null;
}

export type ApprovalDecision = 'allow-once' | 'allow-target' | 'allow-tool' | 'deny';

export interface CodeTextPart {
  kind: 'text';
  segment: number;
  text: string;
}

export interface CodeToolPart {
  kind: 'tool';
  call_id: string;
  name: string;
  input: Record<string, unknown>;
  status: string;
  output?: string;
  options?: ApprovalDecision[];
}

export interface CodeMessage {
  message_id: string;
  role: 'user' | 'assistant';
  origin?: CodeOrigin;
  timestamp?: string;
  text?: string;
  attachments?: string[];
  parts?: Array<CodeTextPart | CodeToolPart>;
  status?: 'streaming' | 'done' | 'stopped' | 'error';
}

// Template de la bibliothèque de prompts (slash commands) — voir
// core/prompt_library.py. Servi par l'endpoint Relay GET /api/prompts.
export interface PromptTemplate {
  id?: string;
  command?: string;
  title?: string;
  description?: string;
  content: string;
}

// =============================================================================
// Agent tool types — see core/agentic_executor.py for the host-side schema.
// =============================================================================

export type ToolName =
  | 'read_file'
  | 'write_file'
  | 'edit_file'
  | 'list_dir'
  | 'glob'
  | 'grep'
  | 'run_command'
  | 'get_active_editor'
  | 'open_file';

export interface ToolCall {
  call_id: string;
  name: ToolName | string;
  input: Record<string, unknown>;
  message_id?: string;
  // Message typed in VS Code (modal confirmation), or on the PC / phone
  // (approval answered from any of the three)
  origin?: CodeOrigin;
}

export interface ToolResult {
  call_id: string;
  content: string;
  is_error: boolean;
}
