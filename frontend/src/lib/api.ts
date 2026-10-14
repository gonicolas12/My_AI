/*
 * Client REST du serveur local (interfaces/desktop/server.py).
 *
 * Le jeton du lancement arrive dans le fragment de l'URL (#token=…) : il est
 * lu une fois, retiré de l'adresse, puis gardé dans sessionStorage pour
 * survivre à un rechargement de la page. Chaque requête le présente.
 */

import type {
  AttachmentView,
  ConversationSnapshot,
  EngineStatus,
  RelayStatus,
  SessionSummary,
  VoiceInputState,
  VoiceOutputState,
} from './events';

const TOKEN_KEY = 'my_ai.token';

let token: string | null = null;

/** Lit le jeton (fragment de l'URL, sinon sessionStorage) et l'ôte de l'adresse. */
export function initToken(): string | null {
  const params = new URLSearchParams(window.location.hash.slice(1));
  const fromHash = params.get('token');
  if (fromHash) {
    token = fromHash;
    try {
      sessionStorage.setItem(TOKEN_KEY, fromHash);
    } catch {
      // stockage indisponible : le jeton reste en mémoire
    }
    params.delete('token');
    const rest = params.toString();
    const url = window.location.pathname + window.location.search + (rest ? `#${rest}` : '');
    window.history.replaceState(null, '', url);
    return token;
  }
  try {
    token = sessionStorage.getItem(TOKEN_KEY);
  } catch {
    token = null;
  }
  return token;
}

export function getToken(): string | null {
  return token;
}

/** Réservé aux tests */
export function setToken(value: string | null): void {
  token = value;
}

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function request<T>(method: string, path: string, body?: unknown): Promise<T> {
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  let payload: BodyInit | undefined;
  if (body instanceof FormData) {
    payload = body;
  } else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }
  let response: Response;
  try {
    response = await fetch(path, { method, headers, body: payload, cache: 'no-store' });
  } catch {
    throw new ApiError(0, 'Le serveur local ne répond pas.');
  }
  if (!response.ok) {
    let detail = `Erreur ${response.status}`;
    try {
      const data = (await response.json()) as { detail?: unknown };
      if (typeof data.detail === 'string') detail = data.detail;
    } catch {
      // corps vide ou non JSON
    }
    throw new ApiError(response.status, detail);
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export interface StatusResponse {
  status: EngineStatus;
  relay: RelayStatus;
  dev: boolean;
  /** Le service de chat répond (GET /api/conversation) */
  chat: boolean;
  /** Seq du dernier événement publié avant la lecture de cet état */
  seq: number;
}

export interface UiState {
  sidebar_open?: boolean;
  /** Largeur du volet d'aperçu (px) */
  preview_width?: number;
}

/** Page d'aperçu du volet de droite (interfaces/desktop/previews.py) */
/** Dossier glissé dans la saisie : les fichiers joints, les images laissées de côté */
export interface FolderAttachments {
  folder: string;
  attachments: AttachmentView[];
  images_skipped: number;
}

export interface PreviewView {
  id: string;
  kind: 'html' | 'svg' | 'document' | 'pdf';
  title: string;
  /** Page à charger dans l'iframe isolée, ou le PDF lui-même */
  url: string;
  /** Document d'origine (aperçu d'un fichier) */
  path: string | null;
}

export interface VoiceStatus {
  input_available: boolean;
  output_available: boolean;
  input_state: VoiceInputState;
  output_state: VoiceOutputState;
  speaking_key: string | null;
  autoread: boolean;
}

/** Résultat de la recherche globale (core/conversation_search.py) */
export interface SearchResult {
  workspace_id: string;
  workspace_name: string;
  message_index: number;
  role: string;
  timestamp: string;
  excerpt: string;
}

export interface FolderView {
  path: string;
  name: string;
  file_count: number;
  chunks: number;
  indexed_at: string;
}

/** Indexation d'un dossier projet en cours */
export interface FolderJob {
  path: string;
  name: string;
  verb: string;
  done: number;
  total: number;
}

export interface FoldersStatus {
  available: boolean;
  session: string | null;
  folders: FolderView[];
  running: FolderJob[];
}

export interface HistoryEntry {
  id: number;
  query: string;
  is_favorite: boolean;
  timestamp: string | null;
}

export type ExportFormat = 'markdown' | 'html' | 'pdf';

export interface SlashCommand {
  command: string;
  title: string;
  description: string;
}

/** Travail sur les modèles Ollama (model_setup.py) : pull, apply (Réglages), install (assistant) */
export type ModelAction = 'pull' | 'apply' | 'install';

export interface ModelJob {
  action: ModelAction;
  name: string;
  running: boolean;
  ok: boolean | null;
  fraction: number;
  status: string;
  message: string;
  log: string[];
}

/** Réglages lus dans config.yaml (settings.py) */
export interface SettingsView {
  base_model: string;
  generation: GenerationParams;
  num_ctx_choices: number[];
  language: string;
  languages: string[];
  relay_auto_start: boolean;
}

export interface GenerationParams {
  temperature: number;
  num_ctx: number;
  timeout: number;
}

/** Modèles d'Ollama : installés (my_ai compris), bases possibles de my_ai */
export interface ModelsView {
  ollama: boolean;
  installed: string[];
  bases: string[];
  base_model: string;
}

/** Assistant de premier lancement : Ollama, matériel, recommandation */
export interface OnboardingInfo {
  ollama: boolean;
  ram_gb: number | null;
  vram_gb: number | null;
  cpu_cores: number | null;
  recommended: string;
  choices: string[];
  job: ModelJob | null;
}

/** Onglets de la Mémoire (memory.py) */
export type MemoryTab = 'facts' | 'document' | 'conversation';

export interface MemoryItem {
  kind: 'fact' | 'vector';
  id: number | string;
  /** Fait */
  category?: string;
  key?: string;
  value?: string;
  source?: string;
  confidence?: number;
  updated_at?: string;
  /** Document ou message de conversation */
  collection?: string;
  content?: string;
  metadata?: Record<string, string | number | boolean | null>;
  provenance: string;
}

export interface MemoryPage {
  items: MemoryItem[];
  total: number;
  page: number;
  pages: number;
  stats: { facts: number; documents: number; conversations: number };
  categories: string[];
}

/** Prompt de la bibliothèque (prompts.py) */
export interface PromptTemplate {
  id: string;
  command: string | null;
  title: string;
  description: string;
  content: string;
  builtin: boolean;
}

export interface PromptFields {
  title: string;
  command: string;
  description: string;
  content: string;
}

const post = <T>(path: string, body?: unknown) => request<T>('POST', path, body);

export const api = {
  status: () => request<StatusResponse>('GET', '/api/status'),
  shutdown: () => request<{ ok: boolean }>('POST', '/api/shutdown'),

  conversation: () => request<ConversationSnapshot>('GET', '/api/conversation'),
  send: (body: {
    text: string;
    attachment_ids?: string[] | null;
    edit_mid?: string | null;
    regenerate?: boolean;
  }) => request<{ request_id: string }>('POST', '/api/conversation/send', body),
  stop: () => request<{ stopped: boolean }>('POST', '/api/conversation/stop'),
  newConversation: () => request<{ ok: boolean }>('POST', '/api/conversation/new'),
  clear: () => request<{ ok: boolean }>('POST', '/api/conversation/clear'),
  save: () => request<{ saved: boolean }>('POST', '/api/conversation/save'),
  navigate: (mid: string, version: number) =>
    request<{ ok: boolean }>('POST', `/api/conversation/branches/${encodeURIComponent(mid)}`, {
      version,
    }),

  sessions: () => request<{ sessions: SessionSummary[] }>('GET', '/api/sessions'),
  loadSession: (id: string) =>
    request<{ ok: boolean }>('POST', `/api/sessions/${encodeURIComponent(id)}/load`),
  deleteSession: (id: string) =>
    request<{ deleted: boolean }>('DELETE', `/api/sessions/${encodeURIComponent(id)}`),

  attachments: () => request<{ attachments: AttachmentView[] }>('GET', '/api/attachments'),
  removeAttachment: (id: string) =>
    request<{ removed: boolean }>('DELETE', `/api/attachments/${encodeURIComponent(id)}`),

  /** Un fichier ; un dossier joint ses fichiers (ChatService.add_folder) */
  addAttachment: (path: string, type?: string) =>
    post<AttachmentView | FolderAttachments>('/api/attachments', { path, type: type ?? null }),
  uploadAttachment: (file: Blob, name: string) => {
    const form = new FormData();
    form.append('file', file, name);
    return post<AttachmentView>('/api/attachments/upload', form);
  },

  rate: (mid: string, score: number) =>
    post<{ rating: number }>(`/api/conversation/messages/${encodeURIComponent(mid)}/rating`, {
      score,
    }),
  slashCommands: (prefix: string) =>
    request<{ commands: SlashCommand[] }>(
      'GET',
      `/api/prompts/commands?prefix=${encodeURIComponent(prefix)}`,
    ),

  fileLinks: (paths: string[]) =>
    post<{ links: Record<string, string | null> }>('/api/files/links', { paths }),
  openFile: (path: string) => post<{ ok: boolean }>('/api/files/open', { path }),
  revealFile: (path: string) => post<{ ok: boolean }>('/api/files/reveal', { path }),
  downloadFile: (path: string) => post<{ path: string }>('/api/files/download', { path }),

  artifactPreview: (body: {
    code: string;
    kind: 'html' | 'svg';
    title: string;
    language: string;
    index: number;
  }) => post<PreviewView>('/api/previews/artifact', body),
  documentPreview: (path: string) => post<PreviewView>('/api/previews/document', { path }),
  previewInBrowser: (id: string) =>
    post<{ path: string }>(`/api/previews/${encodeURIComponent(id)}/browser`),

  editMessage: (mid: string, text: string) =>
    post<{ request_id: string }>('/api/conversation/send', { text, edit_mid: mid }),
  regenerate: (mid: string) =>
    post<{ request_id: string }>('/api/conversation/send', {
      text: '',
      edit_mid: mid,
      regenerate: true,
    }),

  voiceStatus: () => request<VoiceStatus>('GET', '/api/voice'),
  toggleDictation: () => post<{ state: VoiceInputState }>('/api/voice/input'),
  stopDictation: () => post<{ ok: boolean }>('/api/voice/input/stop'),
  speak: (text: string, key: string) =>
    post<{ state: VoiceOutputState }>('/api/voice/speak', { text, key }),
  stopSpeaking: () => post<{ ok: boolean }>('/api/voice/stop'),
  setAutoread: (enabled: boolean) =>
    request<{ autoread: boolean }>('PUT', '/api/voice/autoread', { enabled }),

  search: (query: string) =>
    request<{ available: boolean; results: SearchResult[] }>(
      'GET',
      `/api/search?q=${encodeURIComponent(query)}`,
    ),
  reindexSearch: () => post<{ available: boolean; messages: number }>('/api/search/reindex'),

  folders: () => request<FoldersStatus>('GET', '/api/folders'),
  attachFolder: (path: string) => post<FolderJob>('/api/folders', { path }),
  reindexFolder: (path: string) => post<FolderJob>('/api/folders/reindex', { path }),
  detachFolder: (path: string) => post<{ detached: boolean }>('/api/folders/detach', { path }),

  history: (query: string, favorites: boolean) =>
    request<{ entries: HistoryEntry[] }>(
      'GET',
      `/api/history?q=${encodeURIComponent(query)}&favorites=${favorites ? 'true' : 'false'}`,
    ),
  toggleFavorite: (id: number) => post<{ is_favorite: boolean }>(`/api/history/${id}/favorite`),
  deleteHistory: (id: number) => request<{ deleted: boolean }>('DELETE', `/api/history/${id}`),

  exportConversation: (format: ExportFormat, path: string | null) =>
    post<{ path: string }>('/api/export', { format, path }),

  uiState: () => request<UiState>('GET', '/api/ui'),
  saveUiState: (state: UiState) => request<UiState>('PUT', '/api/ui', state),

  settings: () => request<SettingsView>('GET', '/api/settings'),
  settingsModels: () => request<ModelsView>('GET', '/api/settings/models'),
  modelJob: () => request<{ job: ModelJob | null }>('GET', '/api/settings/models/job'),
  pullModel: (name: string) =>
    post<{ job: ModelJob | null }>('/api/settings/models/pull', { name }),
  applyModel: (name: string) =>
    post<{ job: ModelJob | null }>('/api/settings/models/apply', { name }),
  saveGeneration: (params: GenerationParams) =>
    request<GenerationParams>('PUT', '/api/settings/generation', params),
  setSettingFlag: (name: 'language.default' | 'relay.auto_start', value: string | boolean) =>
    request<SettingsView>('PUT', '/api/settings/flags', { name, value }),
  restartOnboarding: () => post<{ ok: boolean }>('/api/settings/onboarding/restart'),

  memoryPage: (tab: MemoryTab, query: string, category: string | null, page: number) =>
    request<MemoryPage>(
      'GET',
      `/api/memory?tab=${tab}&q=${encodeURIComponent(query)}&page=${page}` +
        (category ? `&category=${encodeURIComponent(category)}` : ''),
    ),
  addFact: (category: string, text: string) =>
    post<{ id: number }>('/api/memory/facts', { category, text }),
  updateMemory: (tab: MemoryTab, id: number | string, text: string) =>
    request<{ ok: boolean }>('PUT', `/api/memory/${tab}/${encodeURIComponent(String(id))}`, {
      text,
    }),
  deleteMemory: (tab: MemoryTab, id: number | string, atSource: boolean) =>
    request<{ ok: boolean }>(
      'DELETE',
      `/api/memory/${tab}/${encodeURIComponent(String(id))}?at_source=${atSource ? 'true' : 'false'}`,
    ),

  prompts: () => request<{ prompts: PromptTemplate[] }>('GET', '/api/prompts'),
  createPrompt: (fields: PromptFields) => post<PromptTemplate>('/api/prompts', fields),
  updatePrompt: (id: string, fields: PromptFields) =>
    request<PromptTemplate>('PUT', `/api/prompts/${encodeURIComponent(id)}`, fields),
  deletePrompt: (id: string) =>
    request<{ ok: boolean }>('DELETE', `/api/prompts/${encodeURIComponent(id)}`),

  onboarding: () => request<OnboardingInfo>('GET', '/api/onboarding'),
  installModel: (name: string) =>
    post<{ job: ModelJob | null }>('/api/onboarding/install', { name }),
  skipOnboarding: () => post<{ ok: boolean }>('/api/onboarding/skip'),
  finishOnboarding: () => post<{ ok: boolean }>('/api/onboarding/finish'),
};
