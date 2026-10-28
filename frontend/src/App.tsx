import { lazy, Suspense, useEffect } from 'react';

import { TooltipProvider } from './components/ui/Tooltip';
import { ChatPage } from './features/chat/ChatPage';
import { CodePage } from './features/code/CodePage';
import { useAutoRead } from './features/chat/useAutoRead';
import { LoadingScreen } from './features/loading/LoadingScreen';
import { CommandPalette } from './features/palette/CommandPalette';
import { Panels } from './features/panels/Panels';
import { Header } from './features/shell/Header';
import { Sidebar } from './features/shell/Sidebar';
import { ScheduledToasts } from './features/shell/ScheduledToasts';
import { Toasts } from './features/shell/Toasts';
import {
  clearConversation,
  newConversation,
  saveConversation,
  stopGeneration,
  toggleSidebar,
} from './lib/actions';
import { api, getToken } from './lib/api';
import { installFocusReport } from './lib/focus';
import { installNavigationGuard, shell } from './lib/shell';
import { installShortcuts, overlayOpen, ownsEscape, type ShortcutHandlers } from './lib/shortcuts';
import { startSync } from './lib/sync';
import { useT } from './i18n';
import { hasSidebar, useApp } from './stores/app';
import { activeOrigin, stopAgentsRun } from './stores/agents';
import { useChat } from './stores/chat';
import { clearCode, stopCode, useCode } from './stores/code';
import { isGenerating } from './stores/chatReducer';
import { togglePalette, usePalette } from './stores/palette';
import { togglePanel } from './stores/panels';
import { clampPreviewWidth, PREVIEW_WIDTH, usePreview } from './stores/preview';

/** Page Agents : chargée à la première ouverture de l'onglet (React Flow compris) */
const AgentsPage = lazy(() => import('./features/agents/AgentsPage'));

/** Raccourcis sans effet pendant que la palette a le clavier (fenêtre à part dans Tk) */
function unlessPalette(handlers: ShortcutHandlers): ShortcutHandlers {
  return Object.fromEntries(
    Object.entries(handlers).map(([combo, handler]) => [
      combo,
      (event: KeyboardEvent) => {
        if (!usePalette.getState().open) handler?.(event);
      },
    ]),
  );
}

function useAppEffects() {
  useEffect(() => startSync(), []);
  useAutoRead();
  useEffect(() => installNavigationGuard(), []);
  useEffect(() => installFocusReport(), []);
  useEffect(() => shell.syncTitleBar(), []);
  useEffect(
    () =>
      installShortcuts({
        'Ctrl+K': () => togglePalette(),
        ...unlessPalette({
          'Ctrl+B': () => {
            if (hasSidebar(useApp.getState().tab)) toggleSidebar();
          },
          'Ctrl+N': () => void newConversation(),
          // Sur la page Code, sa conversation (VS Code, PC et téléphone)
          'Ctrl+L': () =>
            void (useApp.getState().tab === 'code' ? clearCode() : clearConversation()),
          'Ctrl+S': () => void saveConversation(),
          'Ctrl+,': () => togglePanel('settings'),
          // Relay : démarré à l'ouverture du panneau, jamais arrêté par le raccourci (Tk)
          'Ctrl+R': () => togglePanel('relay'),
          F1: () => togglePanel('help'),
        }),
        Escape: (event) => {
          // D6 : Échap arrête la réponse quand aucun dialogue ni menu n'est ouvert,
          // ni un champ qui s'en sert lui-même (recherche à effacer) ; sur la page
          // Agents, il arrête l'exécution lancée d'ici (celle du téléphone ou d'une
          // tâche planifiée s'arrête par le bouton de son fil)
          if (overlayOpen() || ownsEscape(event)) return;
          if (useApp.getState().tab === 'agents') {
            if (activeOrigin() !== 'desktop') return;
            event.preventDefault();
            void stopAgentsRun();
            return;
          }
          if (useApp.getState().tab === 'code') {
            if (!useCode.getState().state.busy) return;
            event.preventDefault();
            void stopCode();
            return;
          }
          if (!isGenerating(useChat.getState())) return;
          event.preventDefault();
          void stopGeneration();
        },
      }),
    [],
  );
  useEffect(() => {
    api
      .uiState()
      .then((state) => {
        useApp.setState({ sidebarOpen: Boolean(state.sidebar_open) });
        usePreview.setState({
          width: clampPreviewWidth(state.preview_width ?? PREVIEW_WIDTH.initial),
        });
      })
      .catch(() => undefined);
  }, []);
}

export function App() {
  const t = useT();
  useAppEffects();
  const connection = useApp((state) => state.connection);
  const status = useApp((state) => state.status);
  const tab = useApp((state) => state.tab);
  // Une fois prêt, l'appli reste affichée : une reconnexion ne la masque pas
  const started = useApp((state) => state.started);

  if (!getToken()) {
    return (
      <div className="flex h-full items-center justify-center px-6 text-center text-fg-2">
        {t('app.tokenMissing')}
      </div>
    );
  }

  return (
    // Infobulles sans contenu cliquable : elles se ferment dès que la souris quitte
    // leur bouton, même vers l'extérieur de la fenêtre
    <TooltipProvider delayDuration={450} skipDelayDuration={200} disableHoverableContent>
      {started ? (
        <div className="flex h-full">
          {hasSidebar(tab) ? <Sidebar /> : null}
          <div className="flex min-w-0 flex-1 flex-col">
            <Header />
            <main className="flex min-h-0 flex-1 flex-col">
              {tab === 'chat' ? (
                <ChatPage />
              ) : tab === 'code' ? (
                <CodePage />
              ) : (
                <Suspense fallback={null}>
                  <AgentsPage />
                </Suspense>
              )}
            </main>
          </div>
        </div>
      ) : (
        <LoadingScreen status={status} connection={connection} />
      )}
      {started ? <Panels /> : null}
      {started ? <CommandPalette /> : null}
      <Toasts />
      <ScheduledToasts />
    </TooltipProvider>
  );
}
