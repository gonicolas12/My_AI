/*
 * Moniteur de ressources de la page Agents (interfaces/desktop/resources.py) :
 * la dernière mesure, et les 60 dernières pour les mini-graphiques
 * (stats_section.py de Tk). Lu à l'ouverture de la page, puis tenu à jour par
 * les événements « resources.sample » : une mesure toutes les 3 s, et une à
 * la fin de chaque agent, qui ajoute un point aux tokens/s.
 */

import { create } from 'zustand';

import { api } from '../lib/api';
import type { ResourceMetrics } from '../lib/events';

/** Points d'un mini-graphique : 60 mesures, environ trois minutes */
export const HISTORY_LENGTH = 60;

export interface ResourcesHistory {
  /** CPU d'Ollama (%) */
  cpu: number[];
  /** RAM d'Ollama (Mo) */
  ram: number[];
  /** GPU (%) */
  gpu: number[];
  /** Tokens/s, un point par agent */
  tps: number[];
}

interface ResourcesState {
  metrics: ResourceMetrics | null;
  history: ResourcesHistory;
  /** Fins d'agents relevées par le serveur */
  inferences: number;
  loaded: boolean;
}

const EMPTY: ResourcesState = {
  metrics: null,
  history: { cpu: [], ram: [], gpu: [], tps: [] },
  inferences: 0,
  loaded: false,
};

export const useResources = create<ResourcesState>()(() => EMPTY);

function push(values: number[], value: number): number[] {
  return [...values, value].slice(-HISTORY_LENGTH);
}

/** Dernière mesure et historique (ouverture de la page ; le moniteur démarre alors) */
export async function loadResources(): Promise<void> {
  try {
    const snapshot = await api.resources();
    useResources.setState({
      metrics: snapshot.metrics,
      history: {
        cpu: snapshot.history.cpu ?? [],
        ram: snapshot.history.ram ?? [],
        gpu: snapshot.history.gpu ?? [],
        tps: snapshot.history.tps ?? [],
      },
      inferences: snapshot.inferences,
      loaded: true,
    });
  } catch {
    // relue à la prochaine ouverture de la page
  }
}

/**
 * Mesure reçue : un point de plus aux courbes CPU, RAM et GPU ; ou, à la fin
 * d'un agent (inferences augmente), un point de plus aux tokens/s.
 */
export function applyResourceSample(sample: {
  metrics: ResourceMetrics;
  inferences: number;
}): void {
  useResources.setState((state) => {
    if (!state.loaded) return state; // la lecture complète suivra
    const { metrics } = sample;
    if (sample.inferences > state.inferences) {
      return {
        metrics,
        inferences: sample.inferences,
        history: { ...state.history, tps: push(state.history.tps, metrics.tokens_per_sec) },
      };
    }
    return {
      metrics,
      history: {
        cpu: push(state.history.cpu, metrics.cpu_percent),
        ram: push(state.history.ram, metrics.ram_used_mb),
        gpu: metrics.gpu_available
          ? push(state.history.gpu, metrics.gpu_percent)
          : state.history.gpu,
        tps: state.history.tps,
      },
    };
  });
}

/** Réservé aux tests */
export function resetResources(): void {
  useResources.setState(EMPTY, true);
}
