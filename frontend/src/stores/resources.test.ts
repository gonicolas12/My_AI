import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { ResourceMetrics } from '../lib/events';
import {
  applyResourceSample,
  HISTORY_LENGTH,
  loadResources,
  resetResources,
  useResources,
} from './resources';

const api = vi.hoisted(() => ({ resources: vi.fn() }));
vi.mock('../lib/api', () => ({ api }));

const METRICS: ResourceMetrics = {
  cpu_percent: 5,
  ram_used_mb: 2900,
  ram_total_mb: 16000,
  ram_percent: 18,
  gpu_available: true,
  gpu_percent: 40,
  gpu_mem_used_mb: 3700,
  gpu_mem_total_mb: 6144,
  inference_ms: 0,
  tokens_per_sec: 0,
};

beforeEach(() => {
  resetResources();
  api.resources.mockResolvedValue({
    metrics: METRICS,
    history: { cpu: [4, 5], ram: [2900, 2900], gpu: [38, 40], tps: [] },
    inferences: 0,
    interval: 3,
  });
});

describe('mesures du moniteur', () => {
  it('attend la lecture complète avant d’ajouter des points', async () => {
    applyResourceSample({ metrics: METRICS, inferences: 0 });
    expect(useResources.getState().metrics).toBeNull();
    await loadResources();
    expect(useResources.getState().history.cpu).toEqual([4, 5]);
  });

  it('une mesure ajoute un point à CPU, RAM et GPU ; une fin d’agent, aux tokens/s', async () => {
    await loadResources();
    applyResourceSample({
      metrics: { ...METRICS, cpu_percent: 9, gpu_percent: 70 },
      inferences: 0,
    });
    let history = useResources.getState().history;
    expect(history.cpu).toEqual([4, 5, 9]);
    expect(history.gpu).toEqual([38, 40, 70]);
    expect(history.tps).toEqual([]);
    applyResourceSample({
      metrics: { ...METRICS, inference_ms: 1800, tokens_per_sec: 41.5 },
      inferences: 1,
    });
    history = useResources.getState().history;
    expect(history.tps).toEqual([41.5]);
    expect(history.cpu).toHaveLength(3);
    expect(useResources.getState().metrics?.tokens_per_sec).toBe(41.5);
  });

  it('garde les 60 dernières mesures, sans point de GPU s’il est illisible', async () => {
    await loadResources();
    for (let index = 0; index < 70; index += 1) {
      applyResourceSample({
        metrics: { ...METRICS, cpu_percent: index, gpu_available: false },
        inferences: 0,
      });
    }
    const history = useResources.getState().history;
    expect(history.cpu).toHaveLength(HISTORY_LENGTH);
    expect(history.cpu.at(-1)).toBe(69);
    expect(history.gpu).toEqual([38, 40]);
  });
});
