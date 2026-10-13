/*
 * Recherche globale dans toutes les conversations (section « Recherche
 * globale » de Tk) : Entrée lance la recherche, Échap l'efface. Un résultat
 * ouvre sa conversation et y surligne le passage trouvé.
 */

import { Bot, RefreshCw, Search, User, X } from 'lucide-react';

import { IconButton } from '../../../components/ui/Button';
import { openSession } from '../../../lib/actions';
import type { SearchResult } from '../../../lib/api';
import { useChat } from '../../../stores/chat';
import { requestHighlight } from '../../../stores/highlight';
import {
  clearSearch,
  reindexSearch,
  runSearch,
  setQuery,
  useSidebar,
} from '../../../stores/sidebar';

async function openResult(result: SearchResult): Promise<void> {
  requestHighlight({
    conversationId: result.workspace_id,
    excerpt: result.excerpt,
    query: useSidebar.getState().searched ?? '',
    messageIndex: result.message_index,
  });
  if (useChat.getState().conversationId !== result.workspace_id) {
    await openSession(result.workspace_id);
  }
}

export function SearchBox() {
  const query = useSidebar((state) => state.query);
  const status = useSidebar((state) => state.searchStatus);
  const searched = useSidebar((state) => state.searched);
  return (
    <div>
      <div className="flex items-center gap-1">
        <label className="flex h-8 min-w-0 flex-1 items-center gap-2 rounded-md border border-line bg-bg px-2.5 text-sm text-fg-2 focus-within:border-line-2">
          <Search size={15} className="shrink-0" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') {
                event.preventDefault();
                void runSearch();
              } else if (event.key === 'Escape' && (query || searched !== null)) {
                event.preventDefault();
                event.stopPropagation();
                clearSearch();
              }
            }}
            placeholder="Rechercher dans tout l’historique…"
            aria-label="Recherche globale"
            data-own-escape={query || searched !== null ? 'true' : undefined}
            className="min-w-0 flex-1 bg-transparent text-fg outline-none placeholder:text-fg-3"
          />
          {query || searched !== null ? (
            <button
              type="button"
              aria-label="Effacer la recherche"
              onClick={clearSearch}
              className="rounded-xs text-fg-3 hover:text-fg"
            >
              <X size={14} />
            </button>
          ) : null}
        </label>
        <IconButton label="Réindexer les conversations" tooltipSide="right" onClick={reindexSearch}>
          <RefreshCw size={15} />
        </IconButton>
      </div>
      {status ? <p className="mt-1 px-1 text-2xs text-fg-3">{status}</p> : null}
    </div>
  );
}

export function SearchResults() {
  const results = useSidebar((state) => state.results);
  const searching = useSidebar((state) => state.searching);
  if (searching && !results.length) return null;
  return (
    <ul className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 pb-2" aria-label="Résultats">
      {results.map((result, index) => {
        const Icon = result.role === 'user' ? User : Bot;
        return (
          <li key={`${result.workspace_id}-${result.message_index}-${index}`}>
            <button
              type="button"
              onClick={() => void openResult(result)}
              title={`[${result.workspace_name}] ${result.excerpt}`}
              className="flex w-full gap-2 rounded-md px-2.5 py-1.5 text-left text-sm text-fg-2 transition-colors duration-150 hover:bg-hover hover:text-fg"
            >
              <Icon size={14} className="mt-0.5 shrink-0 text-fg-3" />
              <span className="min-w-0 flex-1">
                <span className="block truncate text-xs font-medium text-fg">
                  {result.workspace_name}
                </span>
                <span className="line-clamp-2 text-xs leading-snug">{result.excerpt}</span>
              </span>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
