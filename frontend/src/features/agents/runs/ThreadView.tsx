/*
 * Fil ouvert (D32) : la tâche, le plan, puis une section par agent, comme la
 * zone « Résultats » de Tk (output_rendering.py) : liseré à la couleur de
 * l'agent, statut, sortie en Markdown qui s'écrit en direct ; une sortie qui
 * modifie un code fourni se relit en diff (§8).
 */

import { ChevronDown, ChevronRight, Paperclip, Square } from 'lucide-react';
import { createElement, memo, useEffect, useMemo, useRef, useState } from 'react';

import { cn } from '../../../lib/cn';
import type { RunSummary, RunView } from '../../../lib/events';
import { formatDuration } from '../../../lib/format';
import { stopAgentsRun, useAgents } from '../../../stores/agents';
import { summaryOf } from '../../../stores/agentsReducer';
import { CopyButton } from '../../chat/MessageActions';
import { Markdown } from '../../chat/markdown/Markdown';
import { agentColor, agentIcon, NODE_STATUS, RUN_TONE, runTone } from '../agentMeta';
import { DiffView } from './DiffView';
import { type CodeChange, findCodeChange, providedCode } from './diff';
import { clock, useElapsed } from './elapsed';
import { RunKindIcon } from './RunList';
import { planSummary, type ThreadItem, threadItems } from './threadItems';

/** Hauteur maximale d'une sortie avant défilement (Tk : 20 lignes) */
const SECTION_MAX = 560;

function SectionStatus({ item }: { item: ThreadItem }) {
  if (!item.section) {
    return (
      <span className="flex items-center gap-1.5 text-xs text-fg-3">
        <span className="h-2 w-2 rounded-full bg-fg-3" />
        {item.pending === 'skipped' ? 'Non exécuté' : NODE_STATUS.idle.label}
      </span>
    );
  }
  const { status, started_at: started, finished_at: finished } = item.section;
  const meta = NODE_STATUS[status];
  const duration =
    status !== 'running' && started && finished
      ? formatDuration(Date.parse(finished) - Date.parse(started))
      : '';
  return (
    <span className="flex items-center gap-1.5 text-xs" style={{ color: meta.color }}>
      {status === 'running' ? (
        <span className="h-2 w-2 rounded-full bg-warning pulse-soft" />
      ) : (
        <span className="h-2 w-2 rounded-full" style={{ background: meta.color }} />
      )}
      {meta.label}
      {duration ? <span className="text-fg-3"> · {duration}</span> : null}
    </span>
  );
}

const Section = memo(function Section({
  item,
  provided,
}: {
  item: ThreadItem;
  provided: { name: string; text: string }[];
}) {
  const section = item.section;
  const running = section?.status === 'running';
  const [open, setOpen] = useState(true);
  const text = section?.text ?? '';
  // Diff seulement une fois la sortie terminée : pas de calcul à chaque fragment
  const change = useMemo<CodeChange | null>(
    () => (section && section.status !== 'running' ? findCodeChange(text, provided) : null),
    [section, text, provided],
  );
  const [view, setView] = useState<'output' | 'diff' | null>(null);
  const shown = change ? (view ?? 'diff') : 'output';
  // La sortie suit la fin du texte qui s'écrit, sauf si l'utilisateur est remonté
  const body = useRef<HTMLDivElement>(null);
  const pinned = useRef(true);
  useEffect(() => {
    const element = body.current;
    if (element && running && open && pinned.current) element.scrollTop = element.scrollHeight;
  }, [text, running, open]);
  const color = agentColor(item.agentType, item.color);
  const expandable = Boolean(section);

  return (
    <div
      className="overflow-hidden rounded-md border border-line/60 bg-bg-2/70"
      style={{ borderLeft: `3px solid ${color}` }}
    >
      <div className="flex min-h-10 items-center gap-2 px-3">
        <button
          type="button"
          disabled={!expandable}
          aria-expanded={expandable ? open : undefined}
          onClick={() => setOpen(!open)}
          className="flex min-w-0 flex-1 items-center gap-2 py-2 text-left disabled:cursor-default"
        >
          {expandable ? (
            createElement(open ? ChevronDown : ChevronRight, {
              size: 15,
              className: 'shrink-0 text-fg-3',
            })
          ) : (
            <span className="w-[15px] shrink-0" />
          )}
          {createElement(agentIcon(item.agentType), {
            size: 15,
            className: 'shrink-0',
            style: { color },
          })}
          <span className="truncate text-sm font-semibold text-fg">{item.title}</span>
          {item.step ? <span className="shrink-0 text-xs text-fg-3">{item.step}</span> : null}
        </button>
        {change ? (
          <span
            className="flex items-center rounded-md border border-line p-0.5 text-xs"
            role="group"
            aria-label="Affichage de la sortie"
          >
            <button
              type="button"
              aria-pressed={shown === 'output'}
              onClick={() => setView('output')}
              className={cn(
                'rounded px-2 py-0.5',
                shown === 'output' ? 'bg-active text-fg' : 'text-fg-2 hover:text-fg',
              )}
            >
              Sortie
            </button>
            <button
              type="button"
              aria-pressed={shown === 'diff'}
              onClick={() => setView('diff')}
              className={cn(
                'rounded px-2 py-0.5',
                shown === 'diff' ? 'bg-active text-fg' : 'text-fg-2 hover:text-fg',
              )}
            >
              Diff <span className="text-success">+{change.added}</span>{' '}
              <span className="text-error">−{change.removed}</span>
            </button>
          </span>
        ) : null}
        {section && section.text && !running ? (
          <CopyButton text={section.text} label="Copier la sortie" />
        ) : null}
        <SectionStatus item={item} />
      </div>
      {section && open ? (
        <div
          ref={body}
          onScroll={(event) => {
            const element = event.currentTarget;
            pinned.current = element.scrollHeight - element.scrollTop - element.clientHeight < 40;
          }}
          className="overflow-y-auto px-4 pt-0.5 pb-3"
          style={{ maxHeight: SECTION_MAX }}
        >
          {shown === 'diff' && change ? (
            <DiffView change={change} output={text} />
          ) : text ? (
            <Markdown text={text} streaming={running} />
          ) : running ? (
            <p className="shimmer text-sm">L’agent rédige sa réponse…</p>
          ) : (
            <p className="text-sm text-fg-3">Aucune sortie.</p>
          )}
        </div>
      ) : null}
    </div>
  );
});

function RunStatusChip({ run }: { run: RunView }) {
  const running = run.status === 'running';
  const elapsed = useElapsed(run.started_at, running);
  if (running) {
    return (
      <span className="flex items-center gap-1.5 rounded-full bg-warning-soft px-2 py-0.5 text-xs text-warning tabular-nums">
        <span className="h-1.5 w-1.5 rounded-full bg-warning pulse-soft" />
        {RUN_TONE.running.label} · {clock(elapsed)}
      </span>
    );
  }
  const tone = RUN_TONE[runTone(run.status, run.status_text)];
  const duration = formatDuration(run.duration_ms ?? undefined);
  return (
    <span className={cn('rounded-full px-2 py-0.5 text-xs', tone.chip)}>
      {tone.label}
      {duration ? ` · ${duration}` : ''}
    </span>
  );
}

function TaskText({ text }: { text: string }) {
  const [expanded, setExpanded] = useState(false);
  const long = text.length > 280 || text.split('\n').length > 3;
  return (
    <div className="mt-1 text-sm text-fg-2">
      <p className={cn('whitespace-pre-wrap', !expanded && long && 'line-clamp-3')}>{text}</p>
      {long ? (
        <button
          type="button"
          onClick={() => setExpanded(!expanded)}
          className="mt-0.5 text-xs text-fg-3 hover:text-fg"
        >
          {expanded ? 'Réduire' : 'Afficher toute la tâche'}
        </button>
      ) : null}
    </div>
  );
}

/** En-tête du fil, puis ses sections */
function Thread({ run }: { run: RunView }) {
  const summary: RunSummary = useMemo(() => summaryOf(run), [run]);
  const items = useMemo(() => threadItems(run), [run]);
  const provided = useMemo(() => providedCode(run.sources, run.task), [run.sources, run.task]);
  const plan = planSummary(run);
  const running = run.status === 'running';
  const preparing = running && !run.sections.length;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <RunKindIcon run={summary} size={16} />
            <h3 className="text-[15px] font-semibold text-fg">{run.title}</h3>
            <RunStatusChip run={run} />
          </div>
          <TaskText text={run.task} />
          {run.attachments.length ? (
            <p className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-fg-3">
              <Paperclip size={12} />
              {run.attachments.map((item) => (
                <span key={item.path} title={item.path}>
                  {item.name}
                </span>
              ))}
            </p>
          ) : null}
          {plan ? <p className="mt-1 text-xs text-fg-3">{plan}</p> : null}
        </div>
        {running ? (
          <button
            type="button"
            onClick={() => void stopAgentsRun()}
            className="flex h-8 shrink-0 items-center gap-1.5 rounded-md border border-line px-2.5 text-sm text-fg hover:bg-hover"
          >
            <Square size={11} fill="currentColor" />
            Arrêter
          </button>
        ) : null}
      </div>
      {preparing ? (
        <p className="shimmer text-sm">
          {run.attachments.length ? 'Lecture des pièces jointes…' : 'Démarrage des agents…'}
        </p>
      ) : null}
      {items.map((item) => (
        <Section key={item.key} item={item} provided={provided} />
      ))}
      {!running && run.status_text ? (
        <p
          className="text-sm"
          style={{ color: RUN_TONE[runTone(run.status, run.status_text)].color }}
        >
          {run.status_text}
        </p>
      ) : null}
    </div>
  );
}

export function ThreadView() {
  const openRunId = useAgents((state) => state.openRunId);
  const run = useAgents((state) => (openRunId ? state.details[openRunId] : undefined));
  if (!openRunId) return null;
  if (!run) return <p className="shimmer text-sm">Chargement du fil…</p>;
  return <Thread key={run.id} run={run} />;
}
