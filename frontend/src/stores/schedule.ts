/*
 * Tâches planifiées de la page Agents (interfaces/desktop/schedule.py,
 * scheduler_ui.py de Tk). La liste est relue à l'ouverture de la page, après
 * chaque action, et à chaque « scheduler.changed » (fin d'une tâche :
 * dernier résultat et prochaine échéance changent).
 */

import { create } from 'zustand';

import { api, type ScheduledTask, type ScheduleList, type TaskFields } from '../lib/api';
import { notify } from './app';
import { errorText } from './agents';

interface ScheduleState extends ScheduleList {
  loaded: boolean;
}

const EMPTY: ScheduleState = {
  tasks: [],
  croniter: true,
  background: { available: false, registered: false },
  loaded: false,
};

export const useSchedule = create<ScheduleState>()(() => EMPTY);

export async function loadSchedule(): Promise<void> {
  try {
    const list = await api.schedule();
    useSchedule.setState({ ...list, loaded: true });
  } catch {
    // moteur au démarrage : relue à la prochaine ouverture de la page
  }
}

let reloadTimer: ReturnType<typeof setTimeout> | null = null;

/** « scheduler.changed » : relecture regroupée, si la page l'a déjà lue */
export function scheduleChanged(): void {
  if (!useSchedule.getState().loaded) return;
  if (reloadTimer) clearTimeout(reloadTimer);
  reloadTimer = setTimeout(() => {
    reloadTimer = null;
    void loadSchedule();
  }, 200);
}

/** Crée ou modifie une tâche ; l'erreur du serveur remonte au dialogue */
export async function saveScheduledTask(
  id: string | null,
  fields: TaskFields,
): Promise<ScheduledTask> {
  const { task } = id
    ? await api.updateScheduledTask(id, fields)
    : await api.createScheduledTask(fields);
  await loadSchedule();
  return task;
}

async function act(action: () => Promise<unknown>): Promise<boolean> {
  try {
    await action();
    await loadSchedule();
    return true;
  } catch (error) {
    notify('error', errorText(error));
    return false;
  }
}

export function setTaskEnabled(id: string, enabled: boolean): Promise<boolean> {
  return act(() => api.enableScheduledTask(id, enabled));
}

/** ▶ : exécute la tâche tout de suite (son fil apparaît dans « Exécutions ») */
export function runScheduledTask(id: string): Promise<boolean> {
  return act(() => api.runScheduledTask(id));
}

export function deleteScheduledTask(id: string): Promise<boolean> {
  return act(() => api.deleteScheduledTask(id));
}

/** « Exécuter même l'appli fermée » (Planificateur de tâches de Windows) */
export function setScheduleBackground(enabled: boolean): Promise<boolean> {
  return act(() => api.setScheduleBackground(enabled));
}

/** Réservé aux tests */
export function resetSchedule(): void {
  useSchedule.setState(EMPTY, true);
}
