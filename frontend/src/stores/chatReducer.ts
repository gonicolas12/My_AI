/*
 * État du chat côté fenêtre : un instantané du serveur (GET /api/conversation)
 * auquel s'appliquent les événements, dans l'ordre de leur seq.
 *
 * Fonctions pures, sans React : testées dans chatReducer.test.ts.
 */

import type {
  ActiveTurnView,
  AttachmentView,
  ConfirmView,
  ConversationSnapshot,
  MessageView,
  QueueItem,
  ServerEvent,
  Source,
  ToolCallView,
  TurnKind,
} from '../lib/events';

/** Réponse en cours de génération */
export interface LiveTurn {
  mid: string;
  requestId: string;
  kind: TurnKind;
  source: Source;
  /** Bloc « Réflexion » attendu (requête complexe) */
  reasoning: boolean;
  text: string;
  thinking: string;
  /** Jetons de réflexion en cours de réception */
  thinkingActive: boolean;
  thinkingMs: number;
  tools: ToolCallView[];
  documents: string[];
  /** Étape affichée (génération de fichier ou d'image) */
  status: string;
  progress: number | null;
  filename: string | null;
  file: { path: string; name: string } | null;
  image: { path: string; name: string } | null;
  /** Début de la réponse (horloge de la fenêtre, ms) */
  startedAt: number;
}

/** Message de l'utilisateur traité, réponse pas encore commencée */
export interface PendingTurn {
  requestId: string;
  mid: string;
  source: Source;
}

export interface ChatState {
  loaded: boolean;
  conversationId: string | null;
  name: string | null;
  seq: number;
  messages: MessageView[];
  branches: Record<string, { count: number; current: number }>;
  pending: PendingTurn | null;
  live: LiveTurn | null;
  queue: QueueItem[];
  attachments: AttachmentView[];
  confirm: ConfirmView | null;
}

export const initialChatState: ChatState = {
  loaded: false,
  conversationId: null,
  name: null,
  seq: 0,
  messages: [],
  branches: {},
  pending: null,
  live: null,
  queue: [],
  attachments: [],
  confirm: null,
};

/** Une réponse est en cours, ou un message attend la sienne */
export function isGenerating(state: ChatState): boolean {
  return state.live !== null || state.pending !== null;
}

function liveFromView(view: ActiveTurnView): LiveTurn {
  const started = Date.parse(view.started_at);
  return {
    mid: view.mid,
    requestId: view.request_id,
    kind: view.kind,
    source: view.source,
    reasoning: view.reasoning,
    text: view.text,
    thinking: view.thinking,
    thinkingActive: false,
    thinkingMs: 0,
    tools: view.tools.map((tool) => ({ ...tool })),
    documents: [...view.documents],
    status: view.status,
    progress: null,
    filename: view.filename,
    file: null,
    image: null,
    startedAt: Number.isNaN(started) ? Date.now() : started,
  };
}

export function fromSnapshot(snapshot: ConversationSnapshot): ChatState {
  return {
    loaded: true,
    conversationId: snapshot.conversation_id,
    name: snapshot.name,
    seq: snapshot.seq,
    messages: snapshot.messages,
    branches: snapshot.branches,
    pending: null,
    live: snapshot.active ? liveFromView(snapshot.active) : null,
    queue: snapshot.queue,
    attachments: snapshot.attachments,
    confirm: snapshot.confirm,
  };
}

/** Réponse terminée, telle que le serveur la range dans l'historique (_finish_turn) */
function finishedMessage(
  live: LiveTurn,
  text: string,
  extra: Partial<MessageView>,
): MessageView | null {
  if (!text) return null;
  const message: MessageView = {
    mid: live.mid,
    role: 'assistant',
    text,
    timestamp: new Date().toISOString(),
    type:
      live.kind === 'file'
        ? 'file_generation'
        : live.kind === 'image'
          ? 'image_generation'
          : 'text',
    attachments: [],
    image_path: live.image?.path ?? null,
    duration_ms: Date.now() - live.startedAt,
    ...extra,
  };
  if (live.thinking) {
    message.thinking = live.thinking;
    message.thinking_ms = live.thinkingMs;
  }
  const tools = live.tools.filter((tool) => tool.name !== 'synthesis');
  if (tools.length) message.tool_calls = tools;
  if (live.documents.length) message.documents = [...live.documents];
  if (live.file?.path) message.file_path = live.file.path;
  return message;
}

function withLive(state: ChatState, update: (live: LiveTurn) => LiveTurn): ChatState {
  if (!state.live) return state;
  return { ...state, live: update(state.live) };
}

function finish(state: ChatState, message: MessageView | null): ChatState {
  return {
    ...state,
    live: null,
    pending: null,
    messages: message ? [...state.messages, message] : state.messages,
  };
}

/** Applique un événement du chat ; les autres sont ignorés. */
export function reduceChat(state: ChatState, event: ServerEvent): ChatState {
  const next = applyEvent(state, event);
  return next === state ? state : { ...next, seq: Math.max(next.seq, event.seq) };
}

function applyEvent(state: ChatState, event: ServerEvent): ChatState {
  switch (event.type) {
    case 'conversation.loaded': {
      const { snapshot } = (event as ServerEvent<'conversation.loaded'>).payload;
      return fromSnapshot(snapshot);
    }
    case 'queue.updated':
      return { ...state, queue: (event as ServerEvent<'queue.updated'>).payload.items };
    case 'message.user': {
      const p = (event as ServerEvent<'message.user'>).payload;
      const message: MessageView = {
        mid: p.mid,
        role: 'user',
        text: p.text,
        timestamp: p.timestamp,
        type: 'text',
        attachments: p.attachments,
        image_path: p.image_path,
        ...(p.source === 'mobile' ? { source: 'mobile' as const } : {}),
      };
      return {
        ...state,
        // La première réponse d'une conversation crée sa session
        conversationId: event.conversation_id ?? state.conversationId,
        messages: [...state.messages, message],
        pending: { requestId: p.request_id, mid: p.mid, source: p.source },
      };
    }
    case 'assistant.start': {
      const p = (event as ServerEvent<'assistant.start'>).payload;
      return {
        ...state,
        pending: null,
        live: {
          mid: p.mid,
          requestId: p.request_id,
          kind: p.kind,
          source: state.pending?.source ?? 'desktop',
          reasoning: p.reasoning,
          text: '',
          thinking: '',
          thinkingActive: false,
          thinkingMs: 0,
          tools: [],
          documents: [],
          status: '',
          progress: null,
          filename: p.filename,
          file: null,
          image: null,
          startedAt: Date.now(),
        },
      };
    }
    case 'assistant.token': {
      const { text } = (event as ServerEvent<'assistant.token'>).payload;
      return withLive(state, (live) => ({ ...live, text: live.text + text }));
    }
    case 'assistant.sync': {
      const { text } = (event as ServerEvent<'assistant.sync'>).payload;
      return withLive(state, (live) => ({ ...live, text }));
    }
    case 'assistant.thinking': {
      const { text } = (event as ServerEvent<'assistant.thinking'>).payload;
      return withLive(state, (live) => ({
        ...live,
        thinking: live.thinking + text,
        thinkingActive: true,
      }));
    }
    case 'assistant.thinking_done': {
      const { duration_ms } = (event as ServerEvent<'assistant.thinking_done'>).payload;
      return withLive(state, (live) => ({
        ...live,
        thinkingActive: false,
        thinkingMs: duration_ms,
      }));
    }
    case 'tool.call': {
      const p = (event as ServerEvent<'tool.call'>).payload;
      return withLive(state, (live) => ({
        ...live,
        thinkingActive: false,
        tools: [...live.tools, { name: p.name, label: p.label, at: p.at }],
      }));
    }
    case 'tool.result': {
      const p = (event as ServerEvent<'tool.result'>).payload;
      return withLive(state, (live) => {
        const tools = [...live.tools];
        for (let i = tools.length - 1; i >= 0; i -= 1) {
          const tool = tools[i];
          if (tool && tool.name === p.name && tool.ok === undefined) {
            tools[i] = { ...tool, ok: p.ok, summary: p.summary, sources: p.sources };
            break;
          }
        }
        return { ...live, tools };
      });
    }
    case 'document.created': {
      const { path } = (event as ServerEvent<'document.created'>).payload;
      return withLive(state, (live) =>
        live.documents.includes(path) ? live : { ...live, documents: [...live.documents, path] },
      );
    }
    case 'file.created': {
      const p = (event as ServerEvent<'file.created'>).payload;
      return withLive(state, (live) => ({ ...live, file: { path: p.path, name: p.name } }));
    }
    case 'image.progress': {
      const p = (event as ServerEvent<'image.progress'>).payload;
      return withLive(state, (live) => ({ ...live, status: p.message, progress: p.fraction }));
    }
    case 'image.created': {
      const p = (event as ServerEvent<'image.created'>).payload;
      return withLive(state, (live) => ({ ...live, image: { path: p.path, name: p.name } }));
    }
    case 'assistant.done': {
      const p = (event as ServerEvent<'assistant.done'>).payload;
      if (!state.live) return { ...state, pending: null };
      return finish(
        state,
        finishedMessage(state.live, p.text, {
          duration_ms: p.duration_ms,
          ...(p.tokens_per_s ? { tokens_per_s: p.tokens_per_s } : {}),
          ...(p.paths?.length ? { paths: p.paths } : {}),
        }),
      );
    }
    case 'assistant.interrupted': {
      const p = (event as ServerEvent<'assistant.interrupted'>).payload;
      if (!state.live) return { ...state, pending: null };
      return finish(
        state,
        finishedMessage(state.live, p.text, {
          interrupted: true,
          ...(p.paths?.length ? { paths: p.paths } : {}),
        }),
      );
    }
    case 'message.rated': {
      const p = (event as ServerEvent<'message.rated'>).payload;
      return {
        ...state,
        messages: state.messages.map((message) =>
          message.mid === p.mid ? { ...message, rating: p.rating } : message,
        ),
      };
    }
    case 'assistant.error': {
      const p = (event as ServerEvent<'assistant.error'>).payload;
      if (!state.live) return { ...state, pending: null };
      const text = state.live.text || p.message;
      return finish(state, finishedMessage(state.live, text, { error: true }));
    }
    case 'confirm.request':
      return { ...state, confirm: (event as ServerEvent<'confirm.request'>).payload };
    case 'confirm.closed': {
      const p = (event as ServerEvent<'confirm.closed'>).payload;
      return state.confirm?.confirm_id === p.confirm_id ? { ...state, confirm: null } : state;
    }
    case 'attachment.added': {
      const p = (event as ServerEvent<'attachment.added'>).payload;
      if (state.attachments.some((att) => att.id === p.id)) return state;
      return { ...state, attachments: [...state.attachments, p] };
    }
    case 'attachment.ready': {
      const { id } = (event as ServerEvent<'attachment.ready'>).payload;
      return {
        ...state,
        attachments: state.attachments.map((att) =>
          att.id === id ? { ...att, status: 'ready' } : att,
        ),
      };
    }
    case 'attachment.failed': {
      const { id } = (event as ServerEvent<'attachment.failed'>).payload;
      return {
        ...state,
        attachments: state.attachments.map((att) =>
          att.id === id ? { ...att, status: 'error' } : att,
        ),
      };
    }
    case 'attachment.removed': {
      const { id } = (event as ServerEvent<'attachment.removed'>).payload;
      return { ...state, attachments: state.attachments.filter((att) => att.id !== id) };
    }
    default:
      return state;
  }
}
