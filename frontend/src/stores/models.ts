/*
 * Travail sur les modèles Ollama (téléchargement, création de my_ai) : panneau
 * Réglages et assistant de premier lancement.
 *
 * Un travail lancé ici repart d'un état vide avant d'être demandé au serveur :
 * tous ses événements (models.progress, models.log, models.done) arrivent
 * ensuite et s'y ajoutent. Un panneau rouvert relit l'état du serveur
 * (journal compris) avec loadModelJob.
 */

import { create } from 'zustand';

import { api, type ModelAction, type ModelJob } from '../lib/api';
import type { EventPayloads } from '../lib/events';

/** Lignes du journal gardées (comme le serveur) */
const LOG_KEEP = 200;

interface ModelsState {
  job: ModelJob | null;
}

export const useModels = create<ModelsState>()(() => ({ job: null }));

export async function loadModelJob(): Promise<void> {
  try {
    const { job } = await api.modelJob();
    useModels.setState({ job });
  } catch {
    // serveur injoignable : l'état reste celui des événements
  }
}

/** Travail demandé par la fenêtre : état vide, en cours, avant la requête */
export function beginModelJob(action: ModelAction, name: string): void {
  useModels.setState({
    job: { action, name, running: true, ok: null, fraction: 0, status: '', message: '', log: [] },
  });
}

/** Requête refusée (409…) : le travail n'a pas commencé */
export function failModelJob(message: string): void {
  useModels.setState((state) =>
    state.job ? { job: { ...state.job, running: false, ok: false, message } } : state,
  );
}

export function applyModelProgress(payload: EventPayloads['models.progress']): void {
  useModels.setState((state) =>
    state.job
      ? { job: { ...state.job, fraction: payload.fraction, status: payload.status } }
      : state,
  );
}

export function applyModelLog(payload: EventPayloads['models.log']): void {
  useModels.setState((state) =>
    state.job
      ? { job: { ...state.job, log: [...state.job.log, payload.line].slice(-LOG_KEEP) } }
      : state,
  );
}

export function applyModelDone(payload: EventPayloads['models.done']): void {
  useModels.setState((state) =>
    state.job
      ? { job: { ...state.job, running: false, ok: payload.ok, message: payload.message } }
      : state,
  );
}

/** Avancée en clair, comme Tk : « pulling 2f5d… — 42% » */
export function progressLabel(job: Pick<ModelJob, 'fraction' | 'status'>): string {
  if (!job.status && !job.fraction) return '';
  return `${job.status} — ${Math.floor(job.fraction * 100)}%`;
}
