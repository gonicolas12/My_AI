import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { MessageView } from '../lib/events';
import { findResultMessage, highlightTokens } from '../lib/highlight';
import {
  applyFolderProgress,
  applyFoldersChanged,
  clearSearch,
  runSearch,
  searchStatusText,
  setQuery,
  useSidebar,
} from './sidebar';

const api = vi.hoisted(() => ({
  search: vi.fn(),
  folders: vi.fn(() =>
    Promise.resolve({ available: true, session: 's1', folders: [], running: [] }),
  ),
}));
vi.mock('../lib/api', () => ({ api }));

const message = (mid: string, text: string, role: 'user' | 'assistant' = 'assistant') =>
  ({
    mid,
    role,
    text,
    timestamp: null,
    type: 'text',
    attachments: [],
    image_path: null,
  }) as MessageView;

beforeEach(() => {
  vi.clearAllMocks();
  clearSearch();
  useSidebar.setState({ jobs: {} });
});

describe('recherche globale', () => {
  it('affiche le nombre de résultats, ou dit qu’il n’y en a pas', async () => {
    api.search.mockResolvedValueOnce({ available: true, results: [{ excerpt: 'x' }] });
    setQuery('  tuples ');
    await runSearch();
    expect(api.search).toHaveBeenCalledWith('tuples');
    const status = () => searchStatusText(useSidebar.getState().searchStatus);
    expect(status()).toBe('1 résultat');
    api.search.mockResolvedValueOnce({ available: true, results: [] });
    await runSearch();
    expect(status()).toBe('Aucun résultat');
    api.search.mockResolvedValueOnce({ available: false, results: [] });
    await runSearch();
    expect(status()).toBe('Recherche sémantique indisponible');
  });

  it('retrouve le message d’un résultat par son texte, sinon par sa position', () => {
    const messages = [
      message('u1', 'Explique les tuples', 'user'),
      message('a1', 'Les   tuples sont\nimmuables.'),
    ];
    expect(findResultMessage(messages, 'Les tuples sont immuables.', 0)).toBe(1);
    expect(findResultMessage(messages, 'Texte réécrit depuis', 0)).toBe(0);
    expect(findResultMessage(messages, 'Texte réécrit depuis', 9)).toBe(-1);
  });

  it('surligne la requête entière puis ses mots', () => {
    expect(highlightTokens('tuples Python a')).toEqual(['tuples Python a', 'tuples', 'Python']);
    expect(highlightTokens('  ')).toEqual([]);
  });
});

describe('dossiers projet', () => {
  it('suit la progression puis relit la liste à la fin', () => {
    applyFolderProgress({ path: 'C:/p', name: 'p', verb: 'Indexation', done: 10, total: 25 });
    expect(useSidebar.getState().jobs['C:/p']?.done).toBe(10);
    applyFoldersChanged('C:/p');
    expect(useSidebar.getState().jobs['C:/p']).toBeUndefined();
    expect(api.folders).toHaveBeenCalled();
  });
});
