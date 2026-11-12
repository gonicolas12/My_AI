import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useApp } from '../stores/app';
import { renameSession } from './actions';
import type { SessionSummary } from './events';

const api = vi.hoisted(() => ({ renameSession: vi.fn() }));
vi.mock('./api', () => ({ api }));

const sync = vi.hoisted(() => ({ getSocket: vi.fn(() => null), refreshSessions: vi.fn() }));
vi.mock('./sync', () => sync);

const SESSIONS: SessionSummary[] = [
  { id: 's1', name: 'Question A', last_modified: null, message_count: 2, current: true },
  { id: 's2', name: 'Recette', last_modified: null, message_count: 4, current: false },
];

const names = () => useApp.getState().sessions.map((session) => session.name);

beforeEach(() => {
  vi.clearAllMocks();
  useApp.setState({ sessions: SESSIONS, toasts: [] });
});

describe('renameSession', () => {
  it('affiche le nouveau nom tout de suite, puis celui retenu par le serveur', async () => {
    let answer!: (value: { name: string }) => void;
    api.renameSession.mockReturnValue(
      new Promise((resolve) => {
        answer = resolve;
      }),
    );

    const done = renameSession('s1', 'Projet   X');
    expect(names()).toEqual(['Projet   X', 'Recette']);

    answer({ name: 'Projet X' });
    await expect(done).resolves.toBe(true);
    expect(api.renameSession).toHaveBeenCalledWith('s1', 'Projet   X');
    expect(names()).toEqual(['Projet X', 'Recette']);
  });

  it("remet l'ancien nom et affiche le refus du serveur", async () => {
    api.renameSession.mockRejectedValue(new Error('Conversation introuvable.'));

    await expect(renameSession('s1', 'Projet X')).resolves.toBe(false);

    expect(names()).toEqual(['Question A', 'Recette']);
    expect(useApp.getState().toasts.at(-1)?.message).toBe('Conversation introuvable.');
    // La liste est relue : elle reflète ce que le serveur a vraiment enregistré
    expect(sync.refreshSessions).toHaveBeenCalledWith(0);
  });
});
