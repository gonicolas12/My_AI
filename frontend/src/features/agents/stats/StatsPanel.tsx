/*
 * Statistiques et moniteur de ressources de la page Agents (stats_section.py
 * de Tk). Statistiques : tâches exécutées, agents actifs, taux de succès, sur
 * les fils gardés. Ressources d'Ollama : CPU, RAM, GPU, VRAM, temps
 * d'inférence et tokens/s du dernier agent, chacun avec sa barre colorée par
 * seuil (vert sous 50 %, orange sous 80 %, rouge au-delà, comme Tk) et, pour
 * CPU, RAM, GPU et tokens/s, un mini-graphique des 60 dernières mesures.
 */

import { Activity, ChartColumn } from 'lucide-react';
import { memo } from 'react';

import { useT } from '../../../i18n';
import type { ResourceMetrics } from '../../../lib/events';
import { useAgents } from '../../../stores/agents';
import { type ResourcesHistory, useResources } from '../../../stores/resources';
import { meterColor, resourceRows } from './meters';

const SPARK_W = 80;
const SPARK_H = 18;

/** Mini-graphique d'une série (_draw_sparkline de Tk), mis à l'échelle de son maximum */
export const Sparkline = memo(function Sparkline({ values }: { values: number[] }) {
  if (values.length < 2) return <span className="inline-block" style={{ width: SPARK_W }} />;
  const top = Math.max(...values) || 1;
  const step = SPARK_W / (values.length - 1);
  const points = values
    .map((value, index) => {
      const x = index * step;
      const y = SPARK_H - (value / top) * (SPARK_H - 2) - 1;
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(' ');
  return (
    <svg width={SPARK_W} height={SPARK_H} aria-hidden className="shrink-0">
      <polyline
        points={points}
        fill="none"
        stroke="var(--accent)"
        strokeWidth={1.5}
        strokeLinejoin="round"
        strokeLinecap="round"
      />
    </svg>
  );
});

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <div className="text-xs text-fg-2">{label}</div>
      <div className="text-2xl font-semibold text-fg tabular-nums">{value}</div>
    </div>
  );
}

function Statistics() {
  const t = useT();
  const stats = useAgents((state) => state.stats);
  return (
    <div className="rounded-xl border border-line bg-bg-2 p-4">
      <h3 className="mb-3 flex items-center gap-2 text-sm font-semibold text-fg">
        <ChartColumn size={15} className="text-fg-2" />
        {t('stats.title')}
      </h3>
      <div className="grid grid-cols-3 gap-4">
        <Stat label={t('stats.tasks')} value={String(stats.tasks)} />
        <Stat label={t('stats.agents')} value={String(stats.agents)} />
        <Stat
          label={t('stats.successRate')}
          value={
            stats.success_rate === null ? '—' : t('stats.percent', { value: stats.success_rate })
          }
        />
      </div>
      <p className="mt-3 text-xs text-fg-3">{t('stats.note')}</p>
    </div>
  );
}

function MeterRow({
  label,
  percent,
  text,
  color,
  history,
}: {
  label: string;
  percent: number;
  text: string;
  color: string;
  history?: number[];
}) {
  const value = Math.max(0, Math.min(100, percent));
  return (
    <div className="flex items-center gap-3 py-1">
      <span className="w-32 shrink-0 text-sm text-fg-2">{label}</span>
      <div
        role="meter"
        aria-label={label}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(value)}
        aria-valuetext={text}
        className="h-2 min-w-16 flex-1 overflow-hidden rounded-full bg-bg"
      >
        <div
          className="h-full rounded-full transition-[width] duration-300"
          style={{ width: `${value}%`, background: color }}
        />
      </div>
      <span className="w-60 shrink-0 text-end text-sm font-medium whitespace-nowrap text-fg tabular-nums">
        {text}
      </span>
      {history ? <Sparkline values={history} /> : <span style={{ width: SPARK_W }} />}
    </div>
  );
}

function Resources({
  metrics,
  history,
}: {
  metrics: ResourceMetrics | null;
  history: ResourcesHistory;
}) {
  const t = useT();
  return (
    <div className="rounded-xl border border-line bg-bg-2 p-4">
      <h3 className="mb-2 flex items-center gap-2 text-sm font-semibold text-fg">
        <Activity size={15} className="text-fg-2" />
        {t('stats.resources')}
      </h3>
      {metrics ? (
        resourceRows(metrics).map((row) => (
          <MeterRow
            key={row.key}
            label={row.label}
            percent={row.percent}
            text={row.text}
            color={row.threshold ? meterColor(row.percent) : 'var(--info)'}
            history={row.history ? history[row.history] : undefined}
          />
        ))
      ) : (
        <p className="shimmer py-2 text-sm">{t('stats.firstMeasure')}</p>
      )}
      <p className="mt-2 text-xs text-fg-3">{t('stats.resourcesNote')}</p>
    </div>
  );
}

export function StatsPanel() {
  const t = useT();
  const metrics = useResources((state) => state.metrics);
  const history = useResources((state) => state.history);
  return (
    <section aria-labelledby="agents-stats" className="flex flex-col gap-3">
      <h2 id="agents-stats" className="text-lg font-semibold text-fg">
        {t('stats.sectionTitle')}
      </h2>
      <div className="grid items-start gap-4 lg:grid-cols-[minmax(280px,1fr)_2fr]">
        <Statistics />
        <Resources metrics={metrics} history={history} />
      </div>
    </section>
  );
}
