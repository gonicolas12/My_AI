/*
 * Liste des fils d'exécution (D32) : un fil par exécution, avec son statut en
 * direct ; un clic le rouvre à droite. Les 50 derniers restent d'un lancement
 * à l'autre (D33). Un fil lancé du téléphone ou par une tâche planifiée porte
 * son origine (D37).
 */

import {
  CalendarClock,
  Check,
  CircleStop,
  CircleX,
  LoaderCircle,
  Smartphone,
  Swords,
  TriangleAlert,
  Workflow,
  X,
} from 'lucide-react';
import { createElement, memo } from 'react';

import { IconButton } from '../../../components/ui/Button';
import { cn } from '../../../lib/cn';
import type { RunOrigin, RunStatus, RunSummary } from '../../../lib/events';
import { formatDay, formatDuration, formatTime } from '../../../lib/format';
import { deleteRun, openRun, useAgents } from '../../../stores/agents';
import { agentColor, agentIcon, ORIGIN_LABEL, RUN_TONE, runTone } from '../agentMeta';
import { clock, useElapsed } from './elapsed';

export function RunStatusIcon({
  status,
  statusText = '',
  size = 16,
}: {
  status: RunStatus;
  statusText?: string;
  size?: number;
}) {
  const tone = runTone(status, statusText);
  const label = RUN_TONE[tone].label;
  if (tone === 'running') {
    return <LoaderCircle size={size} className="spin text-warning" aria-label={label} />;
  }
  if (tone === 'done') return <Check size={size} className="text-success" aria-label={label} />;
  if (tone === 'partial') {
    return <TriangleAlert size={size} className="text-warning" aria-label={label} />;
  }
  if (tone === 'error') return <CircleX size={size} className="text-error" aria-label={label} />;
  return <CircleStop size={size} className="text-fg-3" aria-label={label} />;
}

/** Icône d'un fil : l'agent pour un agent seul, le workflow sinon */
export function RunKindIcon({ run, size = 13 }: { run: RunSummary; size?: number }) {
  if (run.kind === 'workflow') return <Workflow size={size} className="shrink-0 text-fg-2" />;
  if (run.kind === 'debate') return <Swords size={size} className="shrink-0 text-fg-2" />;
  return createElement(agentIcon(run.agent_type), {
    size,
    className: 'shrink-0',
    style: { color: agentColor(run.agent_type, run.color) },
  });
}

/** Origine d'un fil venu d'ailleurs que la page */
export function OriginIcon({ origin, size = 13 }: { origin: RunOrigin; size?: number }) {
  if (origin === 'desktop') return null;
  return createElement(origin === 'mobile' ? Smartphone : CalendarClock, {
    size,
    className: 'shrink-0 text-fg-3',
    'aria-label': ORIGIN_LABEL[origin],
    role: 'img',
  });
}

/** « 13:55 · 22 s », « hier 18:07 · interrompu », « en cours · 0:48 » */
function RunWhen({ run }: { run: RunSummary }) {
  const running = run.status === 'running';
  const elapsed = useElapsed(run.started_at, running);
  if (running) return <>en cours · {clock(elapsed)}</>;
  const day = formatDay(run.started_at);
  const when =
    day === "Aujourd'hui"
      ? formatTime(run.started_at)
      : `${day.toLowerCase()} ${formatTime(run.started_at)}`;
  const tail =
    run.status === 'interrupted' ? 'interrompu' : formatDuration(run.duration_ms ?? undefined);
  return (
    <>
      {when}
      {tail ? ` · ${tail}` : ''}
    </>
  );
}

/** Ligne d'un fil : re-rendue seulement quand son résumé ou sa sélection change */
const RunRow = memo(function RunRow({ run, selected }: { run: RunSummary; selected: boolean }) {
  return (
    <li className="group/run relative">
      <button
        type="button"
        onClick={() => openRun(run.id)}
        aria-current={selected ? 'true' : undefined}
        className={cn(
          'flex w-full items-start gap-2.5 rounded-md px-2.5 py-2 pr-8 text-left transition-colors duration-150',
          selected ? 'bg-active' : 'hover:bg-hover',
        )}
      >
        <span className="mt-0.5">
          <RunStatusIcon status={run.status} statusText={run.status_text} />
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex items-center gap-1.5">
            <RunKindIcon run={run} />
            <span className="truncate text-sm font-medium text-fg">{run.title}</span>
            <OriginIcon origin={run.origin} />
          </span>
          <span className="block truncate text-xs text-fg-2">{run.task}</span>
          <span className="block text-2xs text-fg-3 tabular-nums">
            <RunWhen run={run} />
          </span>
        </span>
      </button>
      {run.status === 'running' ? null : (
        <span className="absolute top-1.5 right-1.5 opacity-0 transition-opacity duration-150 group-focus-within/run:opacity-100 group-hover/run:opacity-100">
          <IconButton
            size="sm"
            label="Supprimer ce fil"
            tooltipSide="left"
            onClick={() => void deleteRun(run.id)}
            className="hover:text-error"
          >
            <X size={14} />
          </IconButton>
        </span>
      )}
    </li>
  );
});

export function RunList() {
  const runs = useAgents((state) => state.runs);
  const openRunId = useAgents((state) => state.openRunId);
  return (
    <ul className="flex flex-col gap-0.5" aria-label="Fils d'exécution">
      {runs.map((run) => (
        <RunRow key={run.id} run={run} selected={run.id === openRunId} />
      ))}
    </ul>
  );
}
