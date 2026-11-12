import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { t } from '../i18n';
import type { MessageView } from '../lib/events';
import { findResultMessage, highlightTokens } from '../lib/highlight';
import {
  applyFolderProgress,
  applyFoldersChanged,
  clearSearch,
  REINDEX_STATUS_MS,
  reindexSearch,
  runSearch,
  searchStatusText,
  setQuery,
  useSidebar,
  visibleSearchStatus,
} from './sidebar';

const api = vi.hoisted(() => ({
  search: vi.fn(),
  reindexSearch: vi.fn(),
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

describe('réindexation des conversations', () => {
  const shown = () => searchStatusText(visibleSearchStatus(useSidebar.getState()));

  afterEach(() => {
    vi.useRealTimers();
  });

  it('montre le nombre de messages indexés quelques secondes, puis la ligne de la recherche', async () => {
    vi.useFakeTimers();
    api.search.mockResolvedValueOnce({
      available: true,
      results: [{ excerpt: 'x' }, { excerpt: 'y' }],
    });
    setQuery('tuples');
    await runSearch();
    api.reindexSearch.mockResolvedValueOnce({ available: true, messages: 2 });
    const reindexing = reindexSearch();
    expect(shown()).toBe(t('sidebar.search.reindexing'));
    await reindexing;
    expect(shown()).toBe(t('sidebar.search.indexed', { count: 2 }));
    vi.advanceTimersByTime(REINDEX_STATUS_MS - 1);
    expect(shown()).toBe(t('sidebar.search.indexed', { count: 2 }));
    vi.advanceTimersByTime(1);
    expect(shown()).toBe('2 résultats');
  });

  it('n’affiche plus rien après la confirmation quand aucune recherche n’est affichée', async () => {
    vi.useFakeTimers();
    api.reindexSearch.mockResolvedValueOnce({ available: true, messages: 0 });
    await reindexSearch();
    expect(shown()).toBe(t('sidebar.search.indexed', { count: 0 }));
    vi.advanceTimersByTime(REINDEX_STATUS_MS);
    expect(shown()).toBe('');
  });

  it('garde une erreur jusqu’à la recherche suivante', async () => {
    vi.useFakeTimers();
    api.reindexSearch.mockRejectedValueOnce(new Error('serveur arrêté'));
    await reindexSearch();
    vi.advanceTimersByTime(REINDEX_STATUS_MS * 2);
    expect(shown()).toBe(t('common.errorPlain', { error: 'serveur arrêté' }));
    api.search.mockResolvedValueOnce({ available: true, results: [] });
    setQuery('tuples');
    await runSearch();
    expect(shown()).toBe('Aucun résultat');
  });

  it('ignore une réindexation dépassée par une recherche', async () => {
    let finish: (value: { available: boolean; messages: number }) => void = () => undefined;
    api.reindexSearch.mockReturnValueOnce(
      new Promise((resolve) => {
        finish = resolve;
      }),
    );
    const reindexing = reindexSearch();
    api.search.mockResolvedValueOnce({ available: true, results: [] });
    setQuery('tuples');
    await runSearch();
    finish({ available: true, messages: 3 });
    await reindexing;
    expect(shown()).toBe('Aucun résultat');
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
