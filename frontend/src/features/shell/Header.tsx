import { Bot, CircleHelp, MessageSquare, PanelLeft, Trash2 } from 'lucide-react';

import { IconButton } from '../../components/ui/Button';
import { Tooltip } from '../../components/ui/Tooltip';
import { clearConversation, toggleSidebar } from '../../lib/actions';
import { cn } from '../../lib/cn';
import { type MessageKey, useT } from '../../i18n';
import { setTab, useApp, type Tab } from '../../stores/app';
import { openPanel } from '../../stores/panels';
import { useChat } from '../../stores/chat';
import { isGenerating } from '../../stores/chatReducer';

const TABS: { id: Tab; label: MessageKey; icon: typeof Bot }[] = [
  { id: 'chat', label: 'header.tab.chat', icon: MessageSquare },
  { id: 'agents', label: 'header.tab.agents', icon: Bot },
];

/** État de la connexion et du moteur, en pastille */
function StatusDot() {
  const t = useT();
  const connection = useApp((state) => state.connection);
  const status = useApp((state) => state.status);
  let color = 'bg-success';
  let label = t('header.status.connected');
  if (connection !== 'open') {
    color = 'bg-warning pulse-soft';
    label = t('header.status.reconnecting');
  } else if (status?.state === 'error' || status?.ollama === false) {
    color = 'bg-error';
    label = status.error ?? t('header.status.ollamaDown');
  } else if (status?.state !== 'ready') {
    color = 'bg-warning pulse-soft';
    label = status?.label ?? t('header.status.starting');
  } else if (status.placement) {
    label = t('header.status.connectedPlacement', { placement: status.placement });
  }
  return (
    <Tooltip label={label} side="bottom">
      <span
        className="flex h-8 w-8 items-center justify-center"
        role="status"
        aria-label={label}
        tabIndex={0}
      >
        <span className={cn('h-2 w-2 rounded-full', color)} />
      </span>
    </Tooltip>
  );
}

export function Header() {
  const t = useT();
  const tab = useApp((state) => state.tab);
  const sidebarOpen = useApp((state) => state.sidebarOpen);
  const hasMessages = useChat((state) => state.messages.length > 0);
  const busy = useChat(isGenerating);

  return (
    <header className="relative flex h-[var(--header-height)] shrink-0 items-center px-3">
      <div className="flex w-24 items-center">
        {tab === 'chat' && !sidebarOpen ? (
          <IconButton label={t('header.showSidebar')} shortcut="Ctrl+B" onClick={toggleSidebar}>
            <PanelLeft size={18} className="rtl:-scale-x-100" />
          </IconButton>
        ) : null}
      </div>

      <nav
        aria-label={t('header.pages')}
        className="absolute left-1/2 flex -translate-x-1/2 items-center gap-1 rounded-lg border border-line bg-bg-2 p-1"
      >
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            aria-current={tab === id ? 'page' : undefined}
            className={cn(
              'flex h-8 items-center gap-2 rounded-md px-4 text-sm font-semibold transition-colors duration-150',
              tab === id ? 'bg-accent text-on-accent' : 'text-fg-2 hover:bg-hover hover:text-fg',
            )}
          >
            <Icon size={15} />
            {t(label)}
          </button>
        ))}
      </nav>

      <div className="ms-auto flex items-center gap-1">
        {tab === 'chat' && hasMessages ? (
          <IconButton
            label={t('header.clearConversation')}
            shortcut="Ctrl+L"
            disabled={busy}
            onClick={() => void clearConversation()}
          >
            <Trash2 size={17} />
          </IconButton>
        ) : null}
        {tab === 'chat' && hasMessages ? (
          // Comme Tk : à côté d'« Effacer », hors de l'accueil ; F1 ouvre l'aide partout
          <IconButton label={t('header.help')} shortcut="F1" onClick={() => openPanel('help')}>
            <CircleHelp size={17} />
          </IconButton>
        ) : null}
        <StatusDot />
      </div>
    </header>
  );
}
