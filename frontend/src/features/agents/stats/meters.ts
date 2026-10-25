/*
 * Lignes du moniteur de ressources (_apply_resource_metrics de Tk) : part de
 * la barre, texte, couleur par seuil et série du mini-graphique.
 */

import { intlLocale, t } from '../../../i18n';
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

const megabytes = (value: number) => Math.round(value).toLocaleString(intlLocale());

/** « 850 ms », « 13,6 s » */
function inference(ms: number): string {
  return ms < 1000
    ? t('format.ms', { n: Math.round(ms) })
    : t('format.seconds', { n: formatDecimal(ms / 1000) });
}

const percentText = (value: number) => t('stats.percent', { value: formatDecimal(value) });

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
      text: percentText(metrics.cpu_percent),
      threshold: true,
      history: 'cpu',
    },
    {
      key: 'ram',
      label: 'RAM',
      percent: Math.min(metrics.ram_percent, 100),
      text: t('stats.ram', {
        used: megabytes(metrics.ram_used_mb),
        total: megabytes(metrics.ram_total_mb),
        percent: percentText(metrics.ram_percent),
      }),
      threshold: true,
      history: 'ram',
    },
    {
      key: 'gpu',
      label: 'GPU',
      percent: gpu ? metrics.gpu_percent : 0,
      text: gpu ? percentText(metrics.gpu_percent) : t('stats.na'),
      threshold: true,
      history: 'gpu',
    },
    {
      key: 'vram',
      label: 'VRAM',
      percent: vram,
      text: gpu
        ? t('stats.vram', {
            used: megabytes(metrics.gpu_mem_used_mb),
            total: megabytes(metrics.gpu_mem_total_mb),
          })
        : t('stats.na'),
      threshold: true,
    },
    {
      key: 'infer',
      label: t('stats.inference'),
      // 5 s remplissent la barre (Tk)
      percent: Math.min(metrics.inference_ms / 50, 100),
      text: metrics.inference_ms ? inference(metrics.inference_ms) : '—',
      threshold: true,
    },
    {
      key: 'tps',
      label: t('stats.tokensPerSecond'),
      percent: Math.min(metrics.tokens_per_sec, 100),
      text: metrics.tokens_per_sec
        ? t('agents.section.tokensPerSecond', { value: formatDecimal(metrics.tokens_per_sec) })
        : '—',
      threshold: false,
      history: 'tps',
    },
  ];
}
