/*
 * Page Code : la conversation de l'extension VS Code (relay/code_hub.py), lue
 * en entier (GET /api/code) puis tenue à jour par les événements « code.* ».
 * Mêmes règles que la transcription du hub : un message de l'utilisateur ouvre
 * sa réponse ; le texte d'une passe du modèle (segment) arrive en entier ; un
 * appel d'outil change d'état à sa place ; à la fin, un appel resté ouvert est
 * « stopped ». Fonctions pures, testées seules (codeReducer.test.ts).
 */

import type {
  AnyCodeEvent,
  CodeAssistantMessage,
  CodeMessage,
  CodePart,
  CodeSnapshot,
  CodeState,
  CodeToolCall,
} from '../lib/events';

export interface CodeConversation {
  /** Conversation lue au moins une fois : les messages suivent les événements */
  loaded: boolean;
  /** Seq du dernier événement appliqué, ou de la lecture */
  seq: number;
  state: CodeState;
  messages: CodeMessage[];
}

export const NO_CODE_STATE: CodeState = {
  vscode: false,
  workspace: null,
  busy: false,
  message_id: null,
  origin: null,
};

export const EMPTY_CODE: CodeConversation = {
  loaded: false,
  seq: 0,
  state: NO_CODE_STATE,
  messages: [],
};

const OPEN_STATUSES = new Set(['requested', 'awaiting-approval', 'running']);

export function withSnapshot<T extends CodeConversation>(conv: T, snapshot: CodeSnapshot): T {
  return {
    ...conv,
    loaded: true,
    seq: snapshot.seq,
    state: snapshot.state,
    messages: snapshot.messages,
  };
}

/** Réponse en cours ou terminée d'un tour, remplacée par `update` */
function updateReply<T extends CodeConversation>(
  conv: T,
  messageId: string,
  update: (reply: CodeAssistantMessage) => CodeAssistantMessage,
): T {
  const index = conv.messages.findLastIndex(
    (message) => message.role === 'assistant' && message.message_id === messageId,
  );
  if (index < 0) return conv;
  const reply = conv.messages[index] as CodeAssistantMessage;
  const updated = update(reply);
  if (updated === reply) return conv;
  const messages = conv.messages.slice();
  messages[index] = updated;
  return { ...conv, messages };
}

function withText(
  reply: CodeAssistantMessage,
  segment: number,
  text: string,
): CodeAssistantMessage {
  const index = reply.parts.findIndex((part) => part.kind === 'text' && part.segment === segment);
  if (index < 0) {
    // Pas de bulle vide : une passe qui n'écrit qu'un appel d'outil
    if (!text.trim()) return reply;
    return { ...reply, parts: [...reply.parts, { kind: 'text', segment, text }] };
  }
  const part = reply.parts[index] as Extract<CodePart, { kind: 'text' }>;
  if (part.text === text) return reply;
  const parts = reply.parts.slice();
  parts[index] = { ...part, text };
  return { ...reply, parts };
}

function withTool(reply: CodeAssistantMessage, tool: CodeToolCall): CodeAssistantMessage {
  const index = reply.parts.findIndex(
    (part) => part.kind === 'tool' && part.call_id === tool.call_id,
  );
  const part: CodePart = { kind: 'tool', ...tool };
  if (index < 0) return { ...reply, parts: [...reply.parts, part] };
  const parts = reply.parts.slice();
  parts[index] = part;
  return { ...reply, parts };
}

function closeTools(parts: CodePart[]): CodePart[] {
  return parts.map((part) => {
    if (part.kind !== 'tool' || !OPEN_STATUSES.has(part.status)) return part;
    const closed = { ...part, status: 'stopped' as const };
    delete closed.options;
    return closed;
  });
}

export function applyCodeEvent<T extends CodeConversation>(conv: T, event: AnyCodeEvent): T {
  if (event.seq <= conv.seq) return conv;
  const next = { ...conv, seq: event.seq };
  if (event.type === 'code.state') return { ...next, state: event.payload };
  // Messages pas encore lus : la lecture de la page les apportera
  if (!conv.loaded) return next;
  switch (event.type) {
    case 'code.user': {
      const { message_id: messageId, text, origin, timestamp, attachments } = event.payload;
      if (next.messages.some((m) => m.role === 'user' && m.message_id === messageId)) return next;
      return {
        ...next,
        messages: [
          ...next.messages,
          { message_id: messageId, role: 'user', text, origin, timestamp, attachments },
          {
            message_id: messageId,
            role: 'assistant',
            origin,
            timestamp,
            parts: [],
            text: '',
            status: 'streaming',
          },
        ],
      };
    }
    case 'code.chunk': {
      const { message_id: messageId, segment, text } = event.payload;
      return updateReply(next, messageId, (reply) => withText(reply, segment, text));
    }
    case 'code.tool': {
      const { message_id: messageId, ...tool } = event.payload;
      return updateReply(next, messageId, (reply) => withTool(reply, tool));
    }
    case 'code.done': {
      const { message_id: messageId, text, status, duration_ms: durationMs } = event.payload;
      return updateReply(next, messageId, (reply) => ({
        ...reply,
        text,
        status,
        duration_ms: durationMs,
        parts: closeTools(reply.parts),
      }));
    }
    case 'code.cleared':
      return { ...next, messages: [] };
    default:
      return next;
  }
}
