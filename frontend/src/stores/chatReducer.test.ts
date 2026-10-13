import { describe, expect, it } from 'vitest';

import type { ConversationSnapshot, EventPayloads, EventType, ServerEvent } from '../lib/events';
import { fromSnapshot, initialChatState, isGenerating, reduceChat } from './chatReducer';

let seq = 0;

function event<T extends EventType>(
  type: T,
  payload: EventPayloads[T],
  messageId: string | null = null,
): ServerEvent {
  seq += 1;
  return { type, payload, conversation_id: 'conv', message_id: messageId, seq };
}

const SNAPSHOT: ConversationSnapshot = {
  conversation_id: 'conv',
  name: 'Conversation',
  seq: 0,
  messages: [],
  branches: {},
  active: null,
  queue: [],
  attachments: [],
  confirm: null,
  busy: false,
};

function run(...events: ServerEvent[]) {
  return events.reduce(reduceChat, fromSnapshot(SNAPSHOT));
}

describe('reduceChat', () => {
  it('suit une réponse du message à la fin', () => {
    const state = run(
      event('message.user', {
        mid: 'u1',
        request_id: 'r1',
        text: 'Bonjour',
        source: 'desktop',
        timestamp: '2026-10-12T10:00:00',
        attachments: [],
        image_path: null,
      }),
      event('assistant.start', {
        mid: 'a1',
        request_id: 'r1',
        kind: 'chat',
        reasoning: false,
        filename: null,
      }),
      event('assistant.token', { text: 'Bon' }),
      event('assistant.token', { text: 'jour !' }),
      event('assistant.done', {
        mid: 'a1',
        text: 'Bonjour !',
        duration_ms: 900,
        tokens_per_s: 72.4,
      }),
    );
    expect(state.live).toBeNull();
    expect(state.pending).toBeNull();
    expect(isGenerating(state)).toBe(false);
    expect(state.messages.map((m) => [m.role, m.text])).toEqual([
      ['user', 'Bonjour'],
      ['assistant', 'Bonjour !'],
    ]);
    expect(state.messages[1]).toMatchObject({ mid: 'a1', duration_ms: 900, tokens_per_s: 72.4 });
    expect(state.seq).toBe(seq);
  });

  it('attend la réponse entre le message et son début', () => {
    const state = run(
      event('message.user', {
        mid: 'u1',
        request_id: 'r1',
        text: 'Salut',
        source: 'mobile',
        timestamp: '2026-10-12T10:00:00',
        attachments: [],
        image_path: null,
      }),
    );
    expect(isGenerating(state)).toBe(true);
    expect(state.pending).toEqual({ requestId: 'r1', mid: 'u1', source: 'mobile' });
    expect(state.messages[0]?.source).toBe('mobile');
  });

  it('range outils, réflexion et documents comme le serveur (_finish_turn)', () => {
    const state = run(
      event('assistant.start', {
        mid: 'a1',
        request_id: 'r1',
        kind: 'chat',
        reasoning: true,
        filename: null,
      }),
      event('assistant.thinking', { text: '🧠 Analyse :\nJe réfléchis' }),
      event('assistant.thinking_done', { duration_ms: 1200 }),
      event('assistant.token', { text: 'Je cherche.\n' }),
      event('assistant.sync', { text: 'Je cherche.' }),
      event('tool.call', { name: 'web_search', label: '🔍 Recherche', args: {}, at: 11 }),
      event('tool.result', { name: 'web_search', ok: true, summary: '[1] a', sources: 2 }),
      event('assistant.sync', { text: 'Je cherche.\n\n' }),
      event('tool.call', { name: 'synthesis', label: '🧠 Synthèse', args: {}, at: 13 }),
      event('document.created', { path: 'C:/out/rapport.docx', name: 'rapport.docx' }),
      event('assistant.token', { text: 'Voici.' }),
      event('assistant.done', {
        mid: 'a1',
        text: 'Je cherche.\n\nVoici.',
        duration_ms: 3000,
        tokens_per_s: null,
      }),
    );
    const answer = state.messages[0];
    expect(answer?.text).toBe('Je cherche.\n\nVoici.');
    expect(answer?.thinking).toBe('🧠 Analyse :\nJe réfléchis');
    expect(answer?.thinking_ms).toBe(1200);
    // « synthesis » n'est pas rangé, comme dans la session
    expect(answer?.tool_calls).toEqual([
      { name: 'web_search', label: '🔍 Recherche', at: 11, ok: true, summary: '[1] a', sources: 2 },
    ]);
    expect(answer?.documents).toEqual(['C:/out/rapport.docx']);
    expect(answer?.tokens_per_s).toBeUndefined();
  });

  it("n'ajoute pas de réponse interrompue vide", () => {
    const state = run(
      event('assistant.start', {
        mid: 'a1',
        request_id: 'r1',
        kind: 'chat',
        reasoning: false,
        filename: null,
      }),
      event('assistant.interrupted', { mid: 'a1', text: '' }),
    );
    expect(state.messages).toEqual([]);
    expect(state.live).toBeNull();
  });

  it('marque une réponse interrompue ou en erreur', () => {
    const interrupted = run(
      event('assistant.start', {
        mid: 'a1',
        request_id: 'r1',
        kind: 'chat',
        reasoning: false,
        filename: null,
      }),
      event('assistant.token', { text: 'Début' }),
      event('assistant.interrupted', { mid: 'a1', text: 'Début' }),
    );
    expect(interrupted.messages[0]).toMatchObject({ text: 'Début', interrupted: true });

    const failed = run(
      event('assistant.start', {
        mid: 'a2',
        request_id: 'r2',
        kind: 'chat',
        reasoning: false,
        filename: null,
      }),
      event('assistant.error', { mid: 'a2', message: '❌ Erreur IA : délai dépassé' }),
    );
    expect(failed.messages[0]).toMatchObject({ text: '❌ Erreur IA : délai dépassé', error: true });
  });

  it('remplace tout à la réception d’un instantané', () => {
    const before = run(
      event('message.user', {
        mid: 'u1',
        request_id: 'r1',
        text: 'A',
        source: 'desktop',
        timestamp: '2026-10-12T10:00:00',
        attachments: [],
        image_path: null,
      }),
    );
    const snapshot: ConversationSnapshot = {
      ...SNAPSHOT,
      conversation_id: 'autre',
      seq: 99,
      messages: [
        {
          mid: 'x',
          role: 'user',
          text: 'Rechargé',
          timestamp: null,
          type: 'text',
          attachments: [],
          image_path: null,
        },
      ],
    };
    const after = reduceChat(before, event('conversation.loaded', { reason: 'loaded', snapshot }));
    expect(after.conversationId).toBe('autre');
    expect(after.pending).toBeNull();
    expect(after.messages.map((m) => m.text)).toEqual(['Rechargé']);
  });

  it('suit la file, les pièces jointes et les confirmations', () => {
    let state = run(
      event('queue.updated', { items: [{ request_id: 'q', source: 'mobile', text: 'Plus tard' }] }),
      event('attachment.added', {
        id: 'f1',
        path: 'C:/a.pdf',
        name: 'a.pdf',
        type: 'PDF',
        status: 'loading',
      }),
      event('attachment.ready', { id: 'f1' }),
      event('confirm.request', {
        confirm_id: 'c1',
        kind: 'delete_file',
        path: 'C:/a.txt',
        name: 'a.txt',
      }),
    );
    expect(state.queue).toHaveLength(1);
    expect(state.attachments[0]?.status).toBe('ready');
    expect(state.confirm?.confirm_id).toBe('c1');
    state = run(
      event('confirm.request', { confirm_id: 'c1', kind: 'delete_file', path: 'p', name: 'n' }),
      event('confirm.closed', { confirm_id: 'c1', accepted: false }),
      event('attachment.added', { id: 'f2', path: 'p', name: 'n', type: 'Code', status: 'ready' }),
      event('attachment.removed', { id: 'f2' }),
    );
    expect(state.confirm).toBeNull();
    expect(state.attachments).toEqual([]);
  });

  it('ignore les événements hors chat', () => {
    const state = initialChatState;
    expect(reduceChat(state, event('notification', { level: 'info', message: 'x' }))).toBe(state);
  });

  it('garde les chemins cliquables et la note d’une réponse', () => {
    const state = run(
      event('message.user', {
        mid: 'u1',
        request_id: 'r1',
        text: 'Où est le rapport ?',
        source: 'desktop',
        timestamp: '2026-10-12T10:00:00',
        attachments: [],
        image_path: null,
      }),
      event('assistant.start', {
        mid: 'a1',
        request_id: 'r1',
        kind: 'chat',
        reasoning: false,
        filename: null,
      }),
      event('assistant.done', {
        mid: 'a1',
        text: 'Dans C:/out/r.docx',
        duration_ms: 500,
        tokens_per_s: null,
        paths: [{ text: 'C:/out/r.docx', path: 'C:/out/r.docx' }],
      }),
      event('message.rated', { mid: 'a1', rating: 4 }),
    );
    const answer = state.messages[1];
    expect(answer?.paths).toEqual([{ text: 'C:/out/r.docx', path: 'C:/out/r.docx' }]);
    expect(answer?.rating).toBe(4);
    expect(state.messages[0]?.rating).toBeUndefined();
  });
});
