/*
 * Lignes du moniteur de ressources (_apply_resource_metrics de Tk) : part de
 * la barre, texte, couleur par seuil et série du mini-graphique.
 */

import type { ResourceMetrics } from '../../../lib/events';
import { formatDecimal } from '../../../lib/format';
import type { ResourcesHistory } from '../../../stores/resources';

/** Couleur d'une barre (_draw_bar de Tk) : vert sous 50 %, orange sous 80 %, rouge au-delà */
export function meterColor(percent: number): string {
  if (percent < 50) return 'var(--success)';
  if (percent < 80) return 'var(--warning)';
  return 'var(--error)';
}

export interface ResourceRow {
  key: 'cpu' | 'ram' | 'gpu' | 'vram' | 'infer' | 'tps';
  label: string;
  /** Part de la barre (0 à 100) */
  percent: number;
  text: string;
  /** Couleur par seuil ; sinon une couleur neutre (tokens/s : plus c'est haut, mieux c'est) */
  threshold: boolean;
  /** Série du mini-graphique (CPU, RAM, GPU et tokens/s, comme Tk) */
  history?: keyof ResourcesHistory;
}

const megabytes = (value: number) => Math.round(value).toLocaleString('fr-FR');

/** « 850 ms », « 13,6 s » */
function inference(ms: number): string {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${formatDecimal(ms / 1000)} s`;
}

export function resourceRows(metrics: ResourceMetrics): ResourceRow[] {
  const gpu = metrics.gpu_available;
  const vram =
    gpu && metrics.gpu_mem_total_mb > 0
      ? (metrics.gpu_mem_used_mb / metrics.gpu_mem_total_mb) * 100
      : 0;
  return [
    {
      key: 'cpu',
      label: 'CPU',
      percent: metrics.cpu_percent,
      text: `${formatDecimal(metrics.cpu_percent)} %`,
      threshold: true,
      history: 'cpu',
    },
    {
      key: 'ram',
      label: 'RAM',
      percent: Math.min(metrics.ram_percent, 100),
      text: `${megabytes(metrics.ram_used_mb)} Mo / ${megabytes(metrics.ram_total_mb)} Mo (${formatDecimal(metrics.ram_percent)} %)`,
      threshold: true,
      history: 'ram',
    },
    {
      key: 'gpu',
      label: 'GPU',
      percent: gpu ? metrics.gpu_percent : 0,
      text: gpu ? `${formatDecimal(metrics.gpu_percent)} %` : 'N/A',
      threshold: true,
      history: 'gpu',
    },
    {
      key: 'vram',
      label: 'VRAM',
      percent: vram,
      text: gpu
        ? `${megabytes(metrics.gpu_mem_used_mb)} / ${megabytes(metrics.gpu_mem_total_mb)} Mo`
        : 'N/A',
      threshold: true,
    },
    {
      key: 'infer',
      label: 'Temps inférence',
      // 5 s remplissent la barre (Tk)
      percent: Math.min(metrics.inference_ms / 50, 100),
      text: metrics.inference_ms ? inference(metrics.inference_ms) : '—',
      threshold: true,
    },
    {
      key: 'tps',
      label: 'Tokens/sec',
      percent: Math.min(metrics.tokens_per_sec, 100),
      text: metrics.tokens_per_sec ? `${formatDecimal(metrics.tokens_per_sec)} tok/s` : '—',
      threshold: false,
      history: 'tps',
    },
  ];
}
