import { describe, expect, it } from 'vitest';

import type { ResourceMetrics } from '../../../lib/events';
import { meterColor, resourceRows } from './meters';

const METRICS: ResourceMetrics = {
  cpu_percent: 12.34,
  ram_used_mb: 2904.6,
  ram_total_mb: 16204,
  ram_percent: 17.93,
  gpu_available: true,
  gpu_percent: 86,
  gpu_mem_used_mb: 3712,
  gpu_mem_total_mb: 6144,
  inference_ms: 13_560,
  tokens_per_sec: 42.15,
};

describe('moniteur de ressources', () => {
  it('colore les barres par seuil, comme Tk', () => {
    expect(meterColor(0)).toBe('var(--success)');
    expect(meterColor(49.9)).toBe('var(--success)');
    expect(meterColor(50)).toBe('var(--warning)');
    expect(meterColor(79.9)).toBe('var(--warning)');
    expect(meterColor(80)).toBe('var(--error)');
  });

  it('écrit les six lignes de Tk, en nombres français', () => {
    const rows = resourceRows(METRICS);
    expect(rows.map((row) => [row.label, row.text])).toEqual([
      ['CPU', '12,3 %'],
      ['RAM', '2 905 Mo / 16 204 Mo (17,9 %)'],
      ['GPU', '86 %'],
      ['VRAM', '3 712 / 6 144 Mo'],
      ['Temps inférence', '13,6 s'],
      ['Tokens/sec', '42,2 tok/s'],
    ]);
    // 5 s remplissent la barre d'inférence ; tokens/s sans seuil (plus haut = mieux)
    expect(rows[4]?.percent).toBe(100);
    expect(rows[5]?.threshold).toBe(false);
    expect(rows.map((row) => row.history)).toEqual([
      'cpu',
      'ram',
      'gpu',
      undefined,
      undefined,
      'tps',
    ]);
  });

  it('sans GPU lisible ni agent terminé : N/A et tirets', () => {
    const rows = resourceRows({
      ...METRICS,
      gpu_available: false,
      inference_ms: 0,
      tokens_per_sec: 0,
    });
    expect(rows.map((row) => row.text).slice(2)).toEqual(['N/A', 'N/A', '—', '—']);
    expect(rows[2]?.percent).toBe(0);
    expect(resourceRows({ ...METRICS, inference_ms: 850 })[4]?.text).toBe('850 ms');
  });
});
