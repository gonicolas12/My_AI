/*
 * Synchronisation de la fenêtre avec le serveur : flux d'événements, relecture
 * de l'état complet à la (re)connexion, application par lots aux stores.
 *
 * Règle d'ordre : un instantané (GET /api/conversation, /api/status) porte le
 * seq du dernier événement qu'il contient. Les événements reçus pendant sa
 * lecture sont retenus, puis appliqués s'ils sont plus récents que lui.
 */

import { applyAgentEvents, refreshAgentsPage, useAgents } from '../stores/agents';
import { applyChatEvents, setChatSnapshot, useChat } from '../stores/chat';
import { applyModelDone, applyModelLog, applyModelProgress } from '../stores/models';
import { notify, showScheduledResult, useApp } from '../stores/app';
import {
  applyFolderProgress,
  applyFoldersChanged,
  refreshHistory,
  useSidebar,
} from '../stores/sidebar';
import {
  applyTranscript,
  applyVoiceInput,
  applyVoiceOutput,
  loadVoiceStatus,
} from '../stores/voice';
import { ApiError, api, getToken } from './api';
import type { AnyAgentEvent, AnyServerEvent, ServerEvent } from './events';
import { isAgentEvent, isChatEvent } from './events';
import { dispatchDroppedPaths } from './drops';
import { createFrameBatcher } from './scheduleFrame';
import { EventSocket } from './ws';

let socket: EventSocket | null = null;

export function getSocket(): EventSocket | null {
  return socket;
}

function wsUrl(): string {
  const scheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const token = encodeURIComponent(getToken() ?? '');
  return `${scheme}://${window.location.host}/ws?token=${token}`;
}

let sessionsTimer: ReturnType<typeof setTimeout> | null = null;

/** Relit la liste des sessions (regroupé : plusieurs changements, une lecture) */
export function refreshSessions(delay = 250): void {
  if (sessionsTimer) clearTimeout(sessionsTimer);
  sessionsTimer = setTimeout(() => {
    sessionsTimer = null;
    api
      .sessions()
      .then(({ sessions }) => useApp.setState({ sessions }))
      .catch(() => undefined);
  }, delay);
}

export function startSync(): () => void {
  let resyncing = false;
  let held: AnyServerEvent[] = [];
  let statusSeq = 0;
  let resyncAgain = false;

  const applyBatch = (events: AnyServerEvent[]) => {
    const chatFloor = useChat.getState().seq;
    const chatEvents: ServerEvent[] = [];
    const agentEvents: AnyAgentEvent[] = [];
    for (const event of events) {
      if (isAgentEvent(event)) {
        agentEvents.push(event);
        continue;
      }
      if (isChatEvent(event.type)) {
        if (event.seq > chatFloor) chatEvents.push(event);
        continue;
      }
      applyAppEvent(event, statusSeq);
    }
    applyChatEvents(chatEvents);
    applyAgentEvents(agentEvents);
  };

  const batcher = createFrameBatcher<AnyServerEvent>(applyBatch);

  const resync = async () => {
    if (resyncing) {
      resyncAgain = true;
      return;
    }
    resyncing = true;
    try {
      const status = await api.status();
      statusSeq = status.seq;
      useApp.setState((state) => ({
        status: status.status,
        relay: status.relay,
        dev: status.dev,
        started: state.started || status.status.state === 'ready',
      }));
      if (status.status.state === 'ready' || status.chat) {
        await loadConversation();
        refreshSessions(0);
        // Page Agents déjà ouverte : ses fils ont pu avancer pendant la coupure
        if (useAgents.getState().loaded) refreshAgentsPage();
      }
      void loadVoiceStatus();
    } catch {
      // serveur injoignable : la reconnexion relancera la relecture
    } finally {
      resyncing = false;
      const pending = held;
      held = [];
      for (const event of pending) batcher.push(event);
      if (resyncAgain) {
        resyncAgain = false;
        void resync();
      }
    }
  };

  const loadConversation = async () => {
    try {
      setChatSnapshot(await api.conversation());
    } catch (error) {
      if (!(error instanceof ApiError && error.status === 503)) throw error;
    }
  };

  /** Événements hors chat : état de l'appli, notifications */
  const applyAppEvent = (event: ServerEvent, floor: number) => {
    switch (event.type) {
      case 'engine.status': {
        if (event.seq <= floor) return;
        const status = (event as ServerEvent<'engine.status'>).payload;
        const wasReady = useApp.getState().status?.state === 'ready';
        useApp.setState((state) => ({
          status,
          started: state.started || status.state === 'ready',
        }));
        // Moteur prêt : la conversation (rouverte ou vide) peut être lue
        if (status.state === 'ready' && !wasReady) {
          void resync();
        }
        return;
      }
      case 'relay.status':
        if (event.seq > floor) {
          useApp.setState({ relay: (event as ServerEvent<'relay.status'>).payload });
        }
        return;
      case 'notification': {
        const p = (event as ServerEvent<'notification'>).payload;
        notify(p.level, p.message);
        return;
      }
      case 'sessions.changed':
        refreshSessions();
        // Chaque tour enregistre la session : l'historique des requêtes a grandi
        if (useSidebar.getState().sections.history) void refreshHistory();
        return;
      case 'folders.progress':
        applyFolderProgress((event as ServerEvent<'folders.progress'>).payload);
        return;
      case 'models.progress':
        applyModelProgress((event as ServerEvent<'models.progress'>).payload);
        return;
      case 'models.log':
        applyModelLog((event as ServerEvent<'models.log'>).payload);
        return;
      case 'models.done':
        applyModelDone((event as ServerEvent<'models.done'>).payload);
        return;
      case 'folders.changed':
        applyFoldersChanged((event as ServerEvent<'folders.changed'>).payload.path);
        return;
      case 'files.dropped':
        dispatchDroppedPaths((event as ServerEvent<'files.dropped'>).payload.paths);
        return;
      case 'voice.input': {
        const p = (event as ServerEvent<'voice.input'>).payload;
        applyVoiceInput(p.state, p.message);
        return;
      }
      case 'voice.transcript':
        applyTranscript((event as ServerEvent<'voice.transcript'>).payload.text);
        return;
      case 'voice.output': {
        const p = (event as ServerEvent<'voice.output'>).payload;
        applyVoiceOutput(p.state, p.key, p.message);
        return;
      }
      case 'scheduler.result':
        showScheduledResult((event as ServerEvent<'scheduler.result'>).payload);
        return;
      default:
        return;
    }
  };

  socket = new EventSocket(wsUrl, {
    onEvent: (event) => {
      if (resyncing) held.push(event);
      else batcher.push(event);
    },
    onHello: (needResync) => {
      if (needResync) {
        batcher.flushNow();
        void resync();
      }
    },
    onState: (state) => useApp.setState({ connection: state }),
  });
  socket.start();

  return () => {
    socket?.stop();
    socket = null;
  };
}
