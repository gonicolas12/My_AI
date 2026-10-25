/*
 * Barre latérale : recherche globale, dossiers projet, historique des
 * requêtes (sidebar.py de l'interface Tk). Les données viennent du serveur ;
 * ce store garde ce que la barre affiche et les actions qui les rafraîchissent.
 */

import { create } from 'zustand';

import {
  api,
  type FolderJob,
  type FoldersStatus,
  type HistoryEntry,
  type SearchResult,
} from '../lib/api';
import { type MessageKey, type Params, t, type Translate } from '../i18n';
import { notify } from './app';

export type SidebarSection = 'folders' | 'history';

/** Ligne d'état de la recherche : traduite à l'affichage (la langue peut changer) */
export type SearchStatus =
  { key: MessageKey; params?: Params; text?: never } | { key?: never; text: string };

export function searchStatusText(status: SearchStatus | null, translate: Translate = t): string {
  if (!status) return '';
  return status.key ? translate(status.key, status.params) : status.text;
}

interface SidebarState {
  sections: Record<SidebarSection, boolean>;
  // Recherche globale
  query: string;
  /** Requête des résultats affichés (null : pas de recherche) */
  searched: string | null;
  results: SearchResult[];
  searchStatus: SearchStatus | null;
  searching: boolean;
  // Dossiers projet
  folders: FoldersStatus | null;
  jobs: Record<string, FolderJob>;
  // Historique
  historyQuery: string;
  favoritesOnly: boolean;
  history: HistoryEntry[];
}

export const useSidebar = create<SidebarState>()(() => ({
  sections: { folders: false, history: false },
  query: '',
  searched: null,
  results: [],
  searchStatus: null,
  searching: false,
  folders: null,
  jobs: {},
  historyQuery: '',
  favoritesOnly: false,
  history: [],
}));

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

export function toggleSection(section: SidebarSection, open?: boolean): void {
  useSidebar.setState((state) => {
    const next = open ?? !state.sections[section];
    return { sections: { ...state.sections, [section]: next } };
  });
  if (useSidebar.getState().sections[section]) {
    if (section === 'folders') void refreshFolders();
    else void refreshHistory();
  }
}

// ── Recherche globale ───────────────────────────────────────────────────────

export function setQuery(query: string): void {
  useSidebar.setState({ query });
}

export function clearSearch(): void {
  useSidebar.setState({ query: '', searched: null, results: [], searchStatus: null });
}

export async function runSearch(): Promise<void> {
  const query = useSidebar.getState().query.trim();
  if (!query) return;
  useSidebar.setState({
    searching: true,
    searchStatus: { key: 'sidebar.search.running' },
    searched: query,
  });
  try {
    const { available, results } = await api.search(query);
    if (useSidebar.getState().searched !== query) return; // autre recherche entre-temps
    let status: SearchStatus = { key: 'sidebar.search.unavailable' };
    if (available) {
      status = results.length
        ? { key: 'sidebar.search.count', params: { count: results.length } }
        : { key: 'common.noResult' };
    }
    useSidebar.setState({ results, searchStatus: status });
  } catch (error) {
    useSidebar.setState({ results: [], searchStatus: { text: errorText(error) } });
  } finally {
    useSidebar.setState({ searching: false });
  }
}

export async function reindexSearch(): Promise<void> {
  useSidebar.setState({ searchStatus: { key: 'sidebar.search.reindexing' } });
  try {
    const { available, messages } = await api.reindexSearch();
    useSidebar.setState({
      searchStatus: available
        ? { key: 'sidebar.search.indexed', params: { count: messages } }
        : { key: 'sidebar.search.indexUnavailable' },
    });
  } catch (error) {
    useSidebar.setState({
      searchStatus: { key: 'common.errorPlain', params: { error: errorText(error) } },
    });
  }
}

// ── Dossiers projet ─────────────────────────────────────────────────────────

let foldersRequest = 0;

export async function refreshFolders(): Promise<void> {
  const request = ++foldersRequest;
  try {
    const status = await api.folders();
    if (request !== foldersRequest) return;
    const jobs: Record<string, FolderJob> = {};
    for (const job of status.running) jobs[job.path] = job;
    useSidebar.setState({ folders: status, jobs });
  } catch {
    // moteur pas encore prêt : la section se relira à l'ouverture
  }
}

/** Progression d'une indexation (événement folders.progress) */
export function applyFolderProgress(job: FolderJob): void {
  useSidebar.setState((state) => ({ jobs: { ...state.jobs, [job.path]: job } }));
}

/** Indexation finie, dossier détaché (événement folders.changed) */
export function applyFoldersChanged(path: string | null): void {
  useSidebar.setState((state) => {
    if (!path || !state.jobs[path]) return state;
    const jobs = { ...state.jobs };
    delete jobs[path];
    return { jobs };
  });
  void refreshFolders();
}

async function folderAction(action: () => Promise<unknown>): Promise<void> {
  try {
    await action();
  } catch (error) {
    notify('error', errorText(error));
  }
  void refreshFolders();
}

export function attachFolder(path: string): Promise<void> {
  toggleSection('folders', true);
  return folderAction(() => api.attachFolder(path));
}

export function reindexFolder(path: string): Promise<void> {
  return folderAction(() => api.reindexFolder(path));
}

export function detachFolder(path: string): Promise<void> {
  return folderAction(() => api.detachFolder(path));
}

// ── Historique des requêtes ─────────────────────────────────────────────────

let historyRequest = 0;

export async function refreshHistory(): Promise<void> {
  const request = ++historyRequest;
  const { historyQuery, favoritesOnly } = useSidebar.getState();
  try {
    const { entries } = await api.history(historyQuery.trim(), favoritesOnly);
    if (request === historyRequest) useSidebar.setState({ history: entries });
  } catch {
    // historique indisponible : la liste reste vide
  }
}

let historyTimer: ReturnType<typeof setTimeout> | null = null;

export function setHistoryQuery(historyQuery: string): void {
  useSidebar.setState({ historyQuery });
  if (historyTimer) clearTimeout(historyTimer);
  historyTimer = setTimeout(() => void refreshHistory(), 200);
}

export function setFavoritesOnly(favoritesOnly: boolean): void {
  useSidebar.setState({ favoritesOnly });
  void refreshHistory();
}

export async function toggleFavorite(id: number): Promise<void> {
  try {
    await api.toggleFavorite(id);
  } catch (error) {
    notify('error', errorText(error));
  }
  void refreshHistory();
}

export async function deleteHistoryEntry(id: number): Promise<void> {
  try {
    await api.deleteHistory(id);
  } catch (error) {
    notify('error', t('common.errorWith', { error: errorText(error) }));
  }
  void refreshHistory();
}
