import { create } from 'zustand';

import type {
  EngineStatus,
  NotificationLevel,
  RelayStatus,
  SchedulerResult,
  SessionSummary,
} from '../lib/events';
import type { ConnectionState } from '../lib/ws';

/** Code : conversation de l'extension VS Code, ouverte du bouton de la barre latérale */
export type Tab = 'chat' | 'agents' | 'code';

export interface Toast {
  id: number;
  level: NotificationLevel;
  message: string;
}

/** Fin d'une tâche planifiée, en toast (_show_scheduled_toast de Tk) */
export interface ScheduledToast extends SchedulerResult {
  id: number;
}

interface AppState {
  connection: ConnectionState;
  status: EngineStatus | null;
  /** Le moteur a été prêt au moins une fois : l'appli remplace l'écran de chargement */
  started: boolean;
  relay: RelayStatus | null;
  dev: boolean;
  tab: Tab;
  sidebarOpen: boolean;
  sessions: SessionSummary[];
  toasts: Toast[];
  lastScheduled: SchedulerResult | null;
  scheduledToasts: ScheduledToast[];
}

export const useApp = create<AppState>()(() => ({
  connection: 'connecting',
  status: null,
  started: false,
  relay: null,
  dev: false,
  tab: 'chat',
  sidebarOpen: false,
  sessions: [],
  toasts: [],
  lastScheduled: null,
  scheduledToasts: [],
}));

let toastId = 0;

/** Durée d'affichage d'une notification, selon son niveau (Tk : 1,5 à 3 s) */
const TOAST_DURATION: Record<NotificationLevel, number> = {
  info: 2500,
  success: 2000,
  warning: 3500,
  error: 4500,
};

export function notify(level: NotificationLevel, message: string): void {
  const id = ++toastId;
  useApp.setState((state) => ({ toasts: [...state.toasts.slice(-3), { id, level, message }] }));
  setTimeout(() => dismissToast(id), TOAST_DURATION[level]);
}

export function dismissToast(id: number): void {
  useApp.setState((state) => ({ toasts: state.toasts.filter((toast) => toast.id !== id) }));
}

/** Durée d'un toast de tâche planifiée (Tk : 6 s) */
const SCHEDULED_TOAST_DURATION = 6000;

/**
 * Fin d'une tâche planifiée : toast dans l'appli, seulement si le système n'a
 * pas déjà affiché sa notification (os_toast_shown), comme dans Tk
 */
export function showScheduledResult(result: SchedulerResult): void {
  useApp.setState({ lastScheduled: result });
  if (result.os_toast_shown) return;
  const id = ++toastId;
  useApp.setState((state) => ({
    scheduledToasts: [...state.scheduledToasts.slice(-2), { ...result, id }],
  }));
  setTimeout(() => dismissScheduledToast(id), SCHEDULED_TOAST_DURATION);
}

export function dismissScheduledToast(id: number): void {
  useApp.setState((state) => ({
    scheduledToasts: state.scheduledToasts.filter((toast) => toast.id !== id),
  }));
}

export function setTab(tab: Tab): void {
  useApp.setState({ tab });
}

/** Onglets qui ont la barre latérale des conversations : le chat, et la page Code qu'elle ouvre */
export function hasSidebar(tab: Tab): boolean {
  return tab === 'chat' || tab === 'code';
}
