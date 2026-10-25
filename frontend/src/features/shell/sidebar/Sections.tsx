/*
 * Sections repliables de la barre latérale : dossiers projet et historique des
 * requêtes (sidebar.py de l'interface Tk), fermées au lancement comme dans Tk.
 */

import {
  ChevronRight,
  FolderOpen,
  FolderPlus,
  History,
  RefreshCw,
  Search,
  Star,
  Trash2,
  Unlink,
  type LucideIcon,
} from 'lucide-react';
import { type ReactNode, useState } from 'react';

import { IconButton } from '../../../components/ui/Button';
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog';
import type { FolderView, HistoryEntry } from '../../../lib/api';
import { useT } from '../../../i18n';
import { cn } from '../../../lib/cn';
import { setTab } from '../../../stores/app';
import { setDraft } from '../../../stores/composer';
import {
  deleteHistoryEntry,
  detachFolder,
  reindexFolder,
  setFavoritesOnly,
  setHistoryQuery,
  type SidebarSection,
  toggleFavorite,
  toggleSection,
  useSidebar,
} from '../../../stores/sidebar';
import { attachProjectFolder } from './folderActions';

function Section({
  id,
  icon: Icon,
  title,
  count,
  children,
}: {
  id: SidebarSection;
  icon: LucideIcon;
  title: string;
  count?: number | undefined;
  children: ReactNode;
}) {
  const open = useSidebar((state) => state.sections[id]);
  return (
    <div>
      <button
        type="button"
        onClick={() => toggleSection(id)}
        aria-expanded={open}
        className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-sm text-fg-2 transition-colors duration-150 hover:bg-hover hover:text-fg"
      >
        <ChevronRight
          size={14}
          className={cn(
            'shrink-0 transition-transform duration-150 rtl:-scale-x-100',
            open && 'rotate-90 rtl:-rotate-90',
          )}
        />
        <Icon size={15} className="shrink-0" />
        <span className="flex-1 text-start">{title}</span>
        {count ? <span className="text-2xs text-fg-3 tabular-nums">{count}</span> : null}
      </button>
      {open ? (
        <div className="mt-0.5 mb-1 max-h-56 overflow-y-auto ps-6 pe-0.5">{children}</div>
      ) : null}
    </div>
  );
}

const Empty = ({ children }: { children: ReactNode }) => (
  <p className="px-2 py-1 text-xs text-fg-3">{children}</p>
);

// ── Dossiers projet ─────────────────────────────────────────────────────────

function FolderRow({ folder }: { folder: FolderView }) {
  const t = useT();
  const job = useSidebar((state) => state.jobs[folder.path]);
  const [confirming, setConfirming] = useState(false);
  return (
    <li className="group/folder rounded-md px-2 py-1 hover:bg-hover">
      <div className="flex items-center gap-1.5 text-xs">
        <FolderOpen size={13} className="shrink-0 text-fg-3" />
        <span className="min-w-0 flex-1 truncate text-fg" title={folder.path}>
          {folder.name}
        </span>
        <span className="text-2xs text-fg-3 tabular-nums">({folder.file_count})</span>
        <IconButton
          label={t('sidebar.folders.reindex')}
          size="sm"
          tooltipSide="top"
          disabled={Boolean(job)}
          onClick={() => void reindexFolder(folder.path)}
          className="h-6 w-6"
        >
          <RefreshCw size={12} />
        </IconButton>
        <IconButton
          label={t('sidebar.folders.detach')}
          size="sm"
          tooltipSide="top"
          disabled={Boolean(job)}
          onClick={() => setConfirming(true)}
          className="h-6 w-6 hover:text-error!"
        >
          <Unlink size={12} />
        </IconButton>
      </div>
      {job ? <FolderProgress verb={job.verb} done={job.done} total={job.total} /> : null}
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={t('sidebar.folders.detachTitle')}
        message={t('sidebar.folders.detachMessage', { name: folder.name })}
        confirmLabel={t('sidebar.folders.detach')}
        danger
        onConfirm={() => void detachFolder(folder.path)}
      />
    </li>
  );
}

function FolderProgress({ verb, done, total }: { verb: string; done: number; total: number }) {
  const t = useT();
  const ratio = total ? Math.min(1, done / total) : 0;
  return (
    <div className="mt-1 ps-5" role="status" aria-live="polite">
      <div className="h-1 overflow-hidden rounded-full bg-bg-3">
        <div
          className={cn(
            'h-full rounded-full bg-accent transition-[width] duration-200',
            !total && 'w-1/4 pulse-soft',
          )}
          style={total ? { width: `${Math.round(ratio * 100)}%` } : undefined}
        />
      </div>
      <p className="mt-0.5 text-2xs text-fg-3 tabular-nums">
        {total ? t('sidebar.folders.progress', { verb, done, total }) : `${verb}…`}
      </p>
    </div>
  );
}

export function FoldersSection() {
  const t = useT();
  const status = useSidebar((state) => state.folders);
  const jobs = useSidebar((state) => state.jobs);
  const folders = status?.folders ?? [];
  // Dossier en cours d'indexation qui n'est pas encore dans la liste
  const pending = Object.values(jobs).filter(
    (job) => !folders.some((folder) => folder.path === job.path),
  );
  return (
    <Section
      id="folders"
      icon={FolderOpen}
      title={t('sidebar.folders.title')}
      count={folders.length}
    >
      <button
        type="button"
        onClick={() => void attachProjectFolder()}
        className="mb-1 flex w-full items-center gap-2 rounded-md px-2 py-1 text-xs text-fg-2 transition-colors duration-150 hover:bg-hover hover:text-fg"
      >
        <FolderPlus size={13} className="text-accent" />
        {t('sidebar.folders.attach')}
      </button>
      {!status ? null : !status.available ? (
        <Empty>{t('sidebar.folders.unavailable')}</Empty>
      ) : !status.session && !pending.length ? (
        <Empty>{t('sidebar.folders.noSession')}</Empty>
      ) : !folders.length && !pending.length ? (
        <Empty>{t('sidebar.folders.none')}</Empty>
      ) : (
        <ul className="space-y-0.5">
          {folders.map((folder) => (
            <FolderRow key={folder.path} folder={folder} />
          ))}
          {pending.map((job) => (
            <li key={job.path} className="px-2 py-1">
              <div className="flex items-center gap-1.5 text-xs">
                <FolderOpen size={13} className="shrink-0 text-fg-3" />
                <span className="min-w-0 flex-1 truncate text-fg" title={job.path}>
                  {job.name}
                </span>
              </div>
              <FolderProgress verb={job.verb} done={job.done} total={job.total} />
            </li>
          ))}
        </ul>
      )}
    </Section>
  );
}

// ── Historique des requêtes ─────────────────────────────────────────────────

/** Aperçu d'une requête : ses quatre premiers mots (_make_history_entry) */
function preview(query: string): string {
  const words = query.split(/\s+/).filter(Boolean);
  return words.length <= 4 ? query : `${words.slice(0, 4).join(' ')}…`;
}

/** Requête remise dans la zone de saisie du Chat */
function reuse(entry: HistoryEntry) {
  setTab('chat');
  setDraft(entry.query);
  requestAnimationFrame(() => {
    const box = document.querySelector<HTMLTextAreaElement>('textarea[data-composer-input]');
    box?.focus();
    box?.setSelectionRange(entry.query.length, entry.query.length);
  });
}

export function HistorySection() {
  const t = useT();
  const entries = useSidebar((state) => state.history);
  const query = useSidebar((state) => state.historyQuery);
  const favoritesOnly = useSidebar((state) => state.favoritesOnly);
  return (
    <Section id="history" icon={History} title={t('sidebar.history.title')}>
      <label className="mb-1 flex h-7 items-center gap-1.5 rounded-md border border-line bg-bg px-2 text-xs focus-within:border-line-2">
        <Search size={12} className="shrink-0 text-fg-3" />
        <input
          value={query}
          onChange={(event) => setHistoryQuery(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Escape' && query) {
              event.preventDefault();
              setHistoryQuery('');
            }
          }}
          data-own-escape={query ? 'true' : undefined}
          placeholder={t('sidebar.history.search')}
          aria-label={t('sidebar.history.searchLabel')}
          className="min-w-0 flex-1 bg-transparent text-fg outline-none placeholder:text-fg-3"
        />
      </label>
      <label className="mb-1 flex cursor-pointer items-center gap-2 px-1 text-xs text-fg-2">
        <input
          type="checkbox"
          checked={favoritesOnly}
          onChange={(event) => setFavoritesOnly(event.target.checked)}
          className="accent-[var(--accent)]"
        />
        {t('sidebar.history.favoritesOnly')}
      </label>
      {entries.length ? (
        <ul className="space-y-0.5">
          {entries.map((entry) => (
            <li
              key={entry.id}
              className="group/entry flex items-center gap-1 rounded-md pe-1 hover:bg-hover"
            >
              <button
                type="button"
                aria-label={
                  entry.is_favorite
                    ? t('sidebar.history.unfavorite')
                    : t('sidebar.history.favorite')
                }
                aria-pressed={entry.is_favorite}
                onClick={() => void toggleFavorite(entry.id)}
                className="shrink-0 rounded-xs p-1"
              >
                <Star
                  size={12}
                  className={entry.is_favorite ? 'fill-warning text-warning' : 'text-fg-3'}
                />
              </button>
              <button
                type="button"
                onClick={() => reuse(entry)}
                title={entry.query}
                className="min-w-0 flex-1 truncate py-1 text-start text-xs text-fg-2 hover:text-fg"
              >
                {preview(entry.query)}
              </button>
              <button
                type="button"
                aria-label={t('sidebar.history.delete')}
                onClick={() => void deleteHistoryEntry(entry.id)}
                className="shrink-0 rounded-xs p-1 text-fg-3 opacity-0 group-hover/entry:opacity-100 hover:text-error focus-visible:opacity-100"
              >
                <Trash2 size={12} />
              </button>
            </li>
          ))}
        </ul>
      ) : (
        <Empty>{t('common.noResult')}</Empty>
      )}
    </Section>
  );
}
