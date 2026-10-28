import { describe, expect, it } from 'vitest';

import type { AnyCodeEvent, CodeAssistantMessage, CodeSnapshot } from '../lib/events';
import {
  applyCodeEvent,
  EMPTY_CODE,
  NO_CODE_STATE,
  type CodeConversation,
  withSnapshot,
} from './codeReducer';

let seq = 10;
function event<T extends AnyCodeEvent['type']>(
  type: T,
  payload: Extract<AnyCodeEvent, { type: T }>['payload'],
  at?: number,
): AnyCodeEvent {
  seq = at ?? seq + 1;
  return {
    type,
    conversation_id: null,
    message_id: null,
    seq,
    payload,
  } as AnyCodeEvent;
}

function snapshot(overrides: Partial<CodeSnapshot> = {}): CodeSnapshot {
  return {
    state: { ...NO_CODE_STATE, vscode: true, workspace: 'My_AI' },
    messages: [],
    seq: 10,
    ...overrides,
  };
}

function replay(conv: CodeConversation, events: AnyCodeEvent[]): CodeConversation {
  return events.reduce(applyCodeEvent, conv);
}

function reply(conv: CodeConversation): CodeAssistantMessage {
  return conv.messages.at(-1) as CodeAssistantMessage;
}

const USER = {
  message_id: 'code_1',
  role: 'user' as const,
  text: 'Écris a.txt',
  origin: 'mobile' as const,
  timestamp: '2026-10-27T12:00:00',
  attachments: [],
};

describe('applyCodeEvent', () => {
  it('suit l’état de VS Code avant la lecture de la page, sans les messages', () => {
    const conv = replay(EMPTY_CODE, [
      event(
        'code.state',
        { ...NO_CODE_STATE, vscode: true, busy: true, message_id: 'code_1', origin: 'mobile' },
        11,
      ),
      event('code.user', USER),
    ]);
    expect(conv.state.busy).toBe(true);
    expect(conv.messages).toEqual([]);
    expect(conv.seq).toBe(12);
  });

  it('un message ouvre sa réponse, le texte de chaque passe arrive en entier', () => {
    const conv = replay(withSnapshot(EMPTY_CODE, snapshot()), [
      event('code.user', USER, 11),
      event('code.chunk', { message_id: 'code_1', segment: 0, text: 'J’écris' }),
      event('code.chunk', { message_id: 'code_1', segment: 0, text: 'J’écris le fichier.' }),
      // Passe qui n'écrit qu'un appel d'outil : pas de bulle vide
      event('code.chunk', { message_id: 'code_1', segment: 1, text: '  ' }),
    ]);
    expect(conv.messages.map((m) => m.role)).toEqual(['user', 'assistant']);
    expect(reply(conv).status).toBe('streaming');
    expect(reply(conv).origin).toBe('mobile');
    expect(reply(conv).parts).toEqual([{ kind: 'text', segment: 0, text: 'J’écris le fichier.' }]);
  });

  it('un appel d’outil change d’état à sa place, approbation comprise', () => {
    const tool = { call_id: 'c1', name: 'write_file', input: { path: 'a.txt' } };
    const conv = replay(withSnapshot(EMPTY_CODE, snapshot()), [
      event('code.user', USER, 11),
      event('code.chunk', { message_id: 'code_1', segment: 0, text: 'J’écris.' }),
      event('code.tool', { message_id: 'code_1', ...tool, status: 'requested' }),
      event('code.tool', {
        message_id: 'code_1',
        ...tool,
        status: 'awaiting-approval',
        options: ['allow-once', 'deny'],
      }),
    ]);
    const parts = reply(conv).parts;
    expect(parts).toHaveLength(2);
    expect(parts[1]).toMatchObject({
      kind: 'tool',
      status: 'awaiting-approval',
      options: ['allow-once', 'deny'],
    });

    const done = replay(conv, [
      event('code.tool', { message_id: 'code_1', ...tool, status: 'completed', output: 'ok' }),
      event('code.chunk', { message_id: 'code_1', segment: 1, text: 'Fait.' }),
    ]);
    expect(reply(done).parts.map((p) => p.kind)).toEqual(['text', 'tool', 'text']);
    expect(reply(done).parts[1]).toMatchObject({ status: 'completed', output: 'ok' });
  });

  it('la fin de la réponse ferme les appels restés ouverts', () => {
    const conv = replay(withSnapshot(EMPTY_CODE, snapshot()), [
      event('code.user', USER, 11),
      event('code.tool', {
        message_id: 'code_1',
        call_id: 'c1',
        name: 'run_command',
        input: { command: 'npm test' },
        status: 'awaiting-approval',
        options: ['allow-once', 'allow-tool', 'deny'],
      }),
      event('code.done', {
        message_id: 'code_1',
        text: '',
        status: 'stopped',
        timestamp: '2026-10-27T12:00:05',
        duration_ms: 5000,
      }),
    ]);
    expect(reply(conv).status).toBe('stopped');
    expect(reply(conv).duration_ms).toBe(5000);
    expect(reply(conv).parts[0]).toMatchObject({ status: 'stopped' });
    expect(reply(conv).parts[0]).not.toHaveProperty('options');
  });

  it('ignore ce que la lecture contient déjà, efface sur « cleared »', () => {
    const read = withSnapshot(EMPTY_CODE, snapshot({ messages: [USER], seq: 20 }));
    const conv = replay(read, [event('code.user', { ...USER, message_id: 'code_0' }, 19)]);
    expect(conv).toBe(read);
    const twice = replay(read, [event('code.user', USER, 21)]);
    expect(twice.messages).toHaveLength(1);
    const cleared = replay(read, [event('code.cleared', {}, 22)]);
    expect(cleared.messages).toEqual([]);
    expect(cleared.loaded).toBe(true);
  });
});
