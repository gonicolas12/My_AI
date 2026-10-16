/*
 * Barre latérale, consacrée à la navigation : nouvelle conversation,
 * recherche, conversations, dossiers projet, historique. Réglages, Mémoire,
 * Prompts, Relay, lecture automatique et Export sont des boutons discrets en
 * bas. Fermée au lancement la première fois, puis retenue (Ctrl+B).
 */

import {
  BookText,
  Brain,
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
import { formatDay } from '../../lib/format';
import { useApp } from '../../stores/app';
import { useChat } from '../../stores/chat';
import { isGenerating } from '../../stores/chatReducer';
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
  return (
    <li className="group/item relative">
      <button
        type="button"
        onClick={() => void openSession(session.id)}
        aria-current={current ? 'true' : undefined}
        className={cn(
          'flex w-full items-center gap-2 rounded-md py-1.5 pr-8 pl-2.5 text-left text-sm transition-colors duration-150',
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
        aria-label={`Supprimer « ${session.name} »`}
        onClick={() => onDelete(session)}
        className="absolute top-1/2 right-1.5 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-sm text-fg-3 opacity-0 transition-opacity duration-150 group-hover/item:opacity-100 hover:bg-hover hover:text-error focus-visible:opacity-100"
      >
        <Trash2 size={14} />
      </button>
    </li>
  );
}

/** Panneaux ouverts depuis le bas de la barre latérale (aussi par la palette Ctrl+K) */
const PANEL_BUTTONS: { id: PanelId; icon: LucideIcon; label: string; shortcut?: string }[] = [
  { id: 'relay', icon: Radio, label: 'Relay', shortcut: 'Ctrl+R' },
  { id: 'settings', icon: Settings, label: 'Réglages', shortcut: 'Ctrl+,' },
  { id: 'memory', icon: Brain, label: 'Mémoire' },
  { id: 'prompts', icon: BookText, label: 'Prompts' },
];

function PanelButton({ id, icon: Icon, label, shortcut }: (typeof PANEL_BUTTONS)[number]) {
  const open = usePanels((state) => state.open === id);
  return (
    <IconButton
      label={label}
      shortcut={shortcut}
      tooltipSide="top"
      active={open}
      onClick={() => openPanel(id)}
    >
      <Icon size={17} />
    </IconButton>
  );
}

function AutoreadButton() {
  const autoread = useVoice((state) => state.autoread);
  return (
    <IconButton
      label={autoread ? 'Lecture automatique : activée' : 'Lecture automatique : désactivée'}
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
  const open = useApp((state) => state.sidebarOpen);
  const sessions = useApp((state) => state.sessions);
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
      aria-label="Barre latérale"
      aria-hidden={!open}
      inert={!open}
      className={cn(
        'h-full shrink-0 overflow-hidden border-r bg-bg-2 transition-[width,border-color] duration-200 ease-out',
        open ? 'w-[var(--sidebar-width)] border-line' : 'w-0 border-r-0',
      )}
    >
      <div className="flex h-full w-[var(--sidebar-width)] flex-col">
        <div className="flex h-[var(--header-height)] shrink-0 items-center justify-between px-3">
          <span className="pl-1.5 text-lg font-bold text-accent">My_AI</span>
          <IconButton label="Masquer la barre latérale" shortcut="Ctrl+B" onClick={toggleSidebar}>
            <PanelLeftClose size={18} />
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
            Nouvelle conversation
            <kbd className="ml-auto font-sans text-2xs text-fg-3">Ctrl+N</kbd>
          </button>
          <SearchBox />
        </div>

        <div className="mt-3 flex min-h-0 flex-1 flex-col">
          {searching ? (
            <SearchResults />
          ) : (
            <>
              <div className="flex items-center gap-2 px-4 pb-1.5 text-2xs font-semibold tracking-wide text-fg-3 uppercase">
                <MessagesSquare size={13} />
                Conversations
              </div>
              <ul className="min-h-0 flex-1 space-y-0.5 overflow-y-auto px-2 pb-2">
                {sessions.length ? (
                  sessions.map((session) => (
                    <SessionItem
                      key={session.id}
                      session={session}
                      current={session.id === currentId}
                      onDelete={setToDelete}
                    />
                  ))
                ) : (
                  <li className="px-2.5 py-1.5 text-sm text-fg-3">Aucune conversation</li>
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
        title="Supprimer la conversation ?"
        description={toDelete ? `« ${toDelete.name} » sera supprimée définitivement.` : ''}
        footer={
          <>
            <Button variant="secondary" onClick={() => setToDelete(null)}>
              Annuler
            </Button>
            <Button
              variant="danger"
              onClick={() => {
                if (toDelete) void removeSession(toDelete.id);
                setToDelete(null);
              }}
            >
              Supprimer
            </Button>
          </>
        }
      />
    </aside>
  );
}
