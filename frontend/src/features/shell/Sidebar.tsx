/*
 * Barre latérale, consacrée à la navigation : nouvelle conversation, page
 * Code (conversation de l'extension VS Code), recherche, conversations,
 * dossiers projet, historique. Réglages, Mémoire, Prompts, Relay, lecture
 * automatique et Export sont des boutons discrets en bas. Fermée au
 * lancement la première fois, puis retenue (Ctrl+B).
 */

import {
  BookText,
  Brain,
  CodeXml,
  MessagesSquare,
  PanelLeftClose,
  Radio,
  Settings,
  SquarePen,
  Trash2,
  Volume2,
  VolumeX,
  type LucideIcon,
} from 'lucide-react';
import { useEffect, useState } from 'react';

import { Button, IconButton } from '../../components/ui/Button';
import { Dialog } from '../../components/ui/Dialog';
import { newConversation, openSession, removeSession, toggleSidebar } from '../../lib/actions';
import { cn } from '../../lib/cn';
import type { SessionSummary } from '../../lib/events';
import { type MessageKey, useT } from '../../i18n';
import { formatDay } from '../../lib/format';
import { setTab, useApp } from '../../stores/app';
import { useChat } from '../../stores/chat';
import { isGenerating } from '../../stores/chatReducer';
import { useCode } from '../../stores/code';
import { openPanel, type PanelId, usePanels } from '../../stores/panels';
import { refreshFolders, useSidebar } from '../../stores/sidebar';
import { setAutoread, useVoice } from '../../stores/voice';
import { ExportMenu } from './sidebar/ExportMenu';
import { SearchBox, SearchResults } from './sidebar/SearchPanel';
import { FoldersSection, HistorySection } from './sidebar/Sections';

function SessionItem({
  session,
  current,
  onDelete,
}: {
  session: SessionSummary;
  current: boolean;
  onDelete: (session: SessionSummary) => void;
}) {
  const t = useT();
  return (
    <li className="group/item relative">
      <button
        type="button"
        onClick={() => void openSession(session.id)}
        aria-current={current ? 'true' : undefined}
        className={cn(
          'flex w-full items-center gap-2 rounded-md py-1.5 ps-2.5 pe-8 text-start text-sm transition-colors duration-150',
          current ? 'bg-active text-fg' : 'text-fg-2 hover:bg-hover hover:text-fg',
        )}
      >
        <span className="min-w-0 flex-1 truncate">{session.name}</span>
        <span className="shrink-0 text-2xs text-fg-3 group-hover/item:opacity-0">
          {formatDay(session.last_modified)}
        </span>
      </button>
      <button
        type="button"
        aria-label={t('sidebar.deleteNamed', { name: session.name })}
        onClick={() => onDelete(session)}
        className="absolute end-1.5 top-1/2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-sm text-fg-3 opacity-0 transition-opacity duration-150 group-hover/item:opacity-100 hover:bg-hover hover:text-error focus-visible:opacity-100"
      >
        <Trash2 size={14} />
      </button>
    </li>
  );
}

/** Panneaux ouverts depuis le bas de la barre latérale (aussi par la palette Ctrl+K) */
const PANEL_BUTTONS: { id: PanelId; icon: LucideIcon; label: MessageKey; shortcut?: string }[] = [
  { id: 'relay', icon: Radio, label: 'sidebar.panel.relay', shortcut: 'Ctrl+R' },
  { id: 'settings', icon: Settings, label: 'sidebar.panel.settings', shortcut: 'Ctrl+,' },
  { id: 'memory', icon: Brain, label: 'sidebar.panel.memory' },
  { id: 'prompts', icon: BookText, label: 'sidebar.panel.prompts' },
];

function PanelButton({ id, icon: Icon, label, shortcut }: (typeof PANEL_BUTTONS)[number]) {
  const t = useT();
  const open = usePanels((state) => state.open === id);
  return (
    <IconButton
      label={t(label)}
      shortcut={shortcut}
      tooltipSide="top"
      active={open}
      onClick={() => openPanel(id)}
    >
      <Icon size={17} />
    </IconButton>
  );
}

/**
 * Page Code : la conversation de l'extension VS Code. Sa pastille dit si VS
 * Code est connecté au Relay, et s'anime pendant une réponse.
 */
function CodeButton() {
  const t = useT();
  const open = useApp((state) => state.tab === 'code');
  const vscode = useCode((state) => state.state.vscode);
  const busy = useCode((state) => state.state.busy);
  const status = busy
    ? t('code.status.busy')
    : vscode
      ? t('code.status.connected')
      : t('code.status.offline');
  return (
    <button
      type="button"
      onClick={() => setTab('code')}
      aria-current={open ? 'page' : undefined}
      className={cn(
        'flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium transition-colors duration-150',
        open ? 'bg-active text-fg' : 'text-fg hover:bg-hover',
      )}
    >
      <CodeXml size={16} className="text-accent" />
      {t('code.title')}
      <span className="ms-auto flex items-center" title={status}>
        <span className="sr-only">{status}</span>
        <span
          aria-hidden
          className={cn(
            'h-1.5 w-1.5 rounded-full',
            busy ? 'pulse-soft bg-accent' : vscode ? 'bg-success' : 'bg-line-2',
          )}
        />
      </span>
    </button>
  );
}

function AutoreadButton() {
  const t = useT();
  const autoread = useVoice((state) => state.autoread);
  return (
    <IconButton
      label={autoread ? t('sidebar.autoread.on') : t('sidebar.autoread.off')}
      tooltipSide="top"
      aria-pressed={autoread}
      active={autoread}
      onClick={() => void setAutoread(!autoread)}
      className={cn(autoread && 'text-accent hover:text-accent')}
    >
      {autoread ? <Volume2 size={17} /> : <VolumeX size={17} />}
    </IconButton>
  );
}

export function Sidebar() {
  const t = useT();
  const open = useApp((state) => state.sidebarOpen);
  const sessions = useApp((state) => state.sessions);
  // Sur la page Code, aucune conversation du chat n'est celle affichée
  const onCode = useApp((state) => state.tab === 'code');
  const currentId = useChat((state) => state.conversationId);
  const busy = useChat(isGenerating);
  const searching = useSidebar((state) => state.searched !== null);
  const foldersOpen = useSidebar((state) => state.sections.folders);
  const [toDelete, setToDelete] = useState<SessionSummary | null>(null);

  // Les dossiers projet sont ceux de la session courante
  useEffect(() => {
    if (foldersOpen) void refreshFolders();
  }, [currentId, foldersOpen]);

  return (
    <aside
      aria-label={t('sidebar.label')}
      aria-hidden={!open}
      inert={!open}
      className={cn(
        'h-full shrink-0 overflow-hidden border-e bg-bg-2 transition-[width,border-color] duration-200 ease-out',
        open ? 'w-[var(--sidebar-width)] border-line' : 'w-0 border-e-0',
      )}
    >
      <div className="flex h-full w-[var(--sidebar-width)] flex-col">
        <div className="flex h-[var(--header-height)] shrink-0 items-center justify-between px-3">
          <span className="ps-1.5 text-lg font-bold text-accent">My_AI</span>
          <IconButton label={t('sidebar.hide')} shortcut="Ctrl+B" onClick={toggleSidebar}>
            <PanelLeftClose size={18} className="rtl:-scale-x-100" />
          </IconButton>
        </div>

        <div className="space-y-1.5 px-2">
          <button
            type="button"
            disabled={busy}
            onClick={() => void newConversation()}
            className="flex w-full items-center gap-2.5 rounded-md px-2.5 py-2 text-sm font-medium text-fg transition-colors duration-150 hover:bg-hover disabled:text-fg-3 disabled:hover:bg-transparent"
          >
            <SquarePen size={16} className="text-accent" />
            {t('sidebar.newConversation')}
            <kbd className="ms-auto font-sans text-2xs text-fg-3">Ctrl+N</kbd>
          </button>
          <CodeButton />
          <SearchBox />
        </div>

        <div className="mt-3 flex min-h-0 flex-1 flex-col">
          {searching ? (
            <SearchResults />
          ) : (
            <>
              <div className="flex items-center gap-2 px-4 pb-1.5 text-2xs font-semibold tracking-wide text-fg-3 uppercase">
                <MessagesSquare size={13} />
                {t('sidebar.conversations')}
              </div>
              <ul className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 pb-2">
                {sessions.length ? (
                  sessions.map((session) => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      current={!onCode && session.id === currentId}
                      onDelete={setToDelete}
                    />
                  ))
                ) : (
                  <li className="px-2.5 py-1.5 text-sm text-fg-3">{t('sidebar.noConversation')}</li>
                )}
              </ul>
            </>
          )}
          <div className="space-y-0.5 border-t border-line px-2 py-2">
            <FoldersSection />
            <HistorySection />
          </div>
        </div>

        <div className="flex shrink-0 items-center justify-between border-t border-line px-2 py-2">
          <PanelButton {...PANEL_BUTTONS[0]!} />
          <AutoreadButton />
          {PANEL_BUTTONS.slice(1).map((button) => (
            <PanelButton key={button.id} {...button} />
          ))}
          <ExportMenu />
        </div>
      </div>

      <Dialog
        open={toDelete !== null}
        onOpenChange={(value) => {
          if (!value) setToDelete(null);
        }}
        title={t('sidebar.deleteTitle')}
        description={toDelete ? t('sidebar.deleteDescription', { name: toDelete.name }) : ''}
        footer={
          <>
            <Button variant="secondary" onClick={() => setToDelete(null)}>
              {t('common.cancel')}
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                if (toDelete) void removeSession(toDelete.id);
                setToDelete(null);
              }}
            >
              {t('common.delete')}
            </Button>
          </>
        }
      />
    </aside>
  );
}
