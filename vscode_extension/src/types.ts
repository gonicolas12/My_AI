export interface RelayCredentials {
  urls: string[];
  token: string;
  keyB64u: string;
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
  // ordre, comme Claude Code.
  segment_index?: number;
  // tool_use
  call_id?: string;
  name?: string;
  input?: Record<string, unknown>;
  // hello_ack
  server?: string;
  client_kind?: string;
  agentic_enabled?: boolean;
}

export interface HistoryItem {
  text: string;
  is_user: boolean;
  message_id?: string;
  timestamp?: string;
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
}

export interface ToolResult {
  call_id: string;
  content: string;
  is_error: boolean;
}
