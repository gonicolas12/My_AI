/*
 * Fil ouvert (D32) : la tâche, le plan, puis une section par agent, comme la
 * zone « Résultats » de Tk (output_rendering.py) : liseré à la couleur de
 * l'agent, statut, sortie en Markdown qui s'écrit en direct ; une sortie qui
 * modifie un code fourni se relit en diff (§8). Un agent d'une étape parallèle
 * que le modèle n'a pas encore servi « attend son tour » (queuedBehind).
 * Chaque agent terminé affiche sa durée et ses tokens/s ; un fil lancé du
 * téléphone ou par une tâche planifiée le dit, et le second mène à son rapport.
 */

import { ChevronDown, ChevronRight, FileText, Paperclip, Square } from 'lucide-react';
import { createElement, memo, useEffect, useMemo, useRef, useState } from 'react';

import { type Translate, useT } from '../../../i18n';
import { openFile } from '../../../lib/actions';
import { cn } from '../../../lib/cn';
import type { RunSummary, RunView } from '../../../lib/events';
import { formatDecimal, formatDuration } from '../../../lib/format';
import { stopAgentsRun, useAgents } from '../../../stores/agents';
import { summaryOf } from '../../../stores/agentsReducer';
import { CopyButton } from '../../chat/MessageActions';
import { buildChatLinks, citationKey } from '../../chat/markdown/links';
import { Markdown } from '../../chat/markdown/Markdown';
import { splitSources } from '../../chat/markdown/sources';
import { SourcesButton } from '../../chat/SourcesButton';
import {
  agentColor,
  agentIcon,
  NODE_STATUS,
  ORIGIN_LABEL,
  QUEUED,
  RUN_TONE,
  runTone,
} from '../agentMeta';
import { DiffView } from './DiffView';
import { type CodeChange, findCodeChange, providedCode } from './diff';
import { clock, useElapsed } from './elapsed';
import { OriginIcon, RunKindIcon } from './RunList';
import {
  debateSummary,
  planSummary,
  queuedBehind,
  type ThreadItem,
  threadItems,
} from './threadItems';

/** Hauteur maximale d'une sortie avant défilement (Tk : 20 lignes) */
const SECTION_MAX = 560;

function SectionStatus({ item, behind }: { item: ThreadItem; behind?: string }) {
  const t = useT();
  if (!item.section) {
    return (
      <span className="flex items-center gap-1.5 text-xs text-fg-3">
        <span className="h-2 w-2 rounded-full bg-fg-3" />
        {item.pending === 'skipped' ? t('agents.section.notRun') : t(NODE_STATUS.idle.label)}
      </span>
    );
  }
  if (behind) {
    return (
      <span className="flex items-center gap-1.5 text-xs" style={{ color: QUEUED.color }}>
        <span className="h-2 w-2 rounded-full pulse-soft" style={{ background: QUEUED.color }} />
        {t(QUEUED.label)}
      </span>
    );
  }
  const { status, started_at: started, finished_at: finished } = item.section;
  const meta = NODE_STATUS[status];
  const duration =
    status !== 'running' && started && finished
      ? formatDuration(Date.parse(finished) - Date.parse(started))
      : '';
  const speed = item.section.tokens_per_sec;
  return (
    <span className="flex items-center gap-1.5 text-xs" style={{ color: meta.color }}>
      {status === 'running' ? (
        <span className="h-2 w-2 rounded-full bg-warning pulse-soft" />
      ) : (
        <span className="h-2 w-2 rounded-full" style={{ background: meta.color }} />
      )}
      {t(meta.label)}
      {duration ? <span className="text-fg-3"> · {duration}</span> : null}
      {speed ? (
        <span className="text-fg-3 tabular-nums">
          {' '}
          · {t('agents.section.tokensPerSecond', { value: formatDecimal(speed) })}
        </span>
      ) : null}
    </span>
  );
}

const Section = memo(function Section({
  item,
  provided,
  behind,
}: {
  item: ThreadItem;
  provided: { name: string; text: string }[];
  /** Agent que le modèle sert pendant que celui-ci attend son tour */
  behind?: string;
}) {
  const t = useT();
  const section = item.section;
  const running = section?.status === 'running';
  const [open, setOpen] = useState(true);
  const text = section?.text ?? '';
  // Citations « [n] » du bloc Sources (WebAgent) cliquables, comme dans le chat ;
  // le bloc lui-même passe sous le bouton Sources de l'en-tête
  const citations = useMemo(() => citationKey(text), [text]);
  const links = useMemo(() => buildChatLinks(citations, undefined), [citations]);
  const { body: output, sources } = useMemo(() => splitSources(text), [text]);
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
      style={{ borderInlineStart: `3px solid ${color}` }}
    >
      <div className="flex min-h-10 items-center gap-2 px-3">
        <button
          type="button"
          disabled={!expandable}
          aria-expanded={expandable ? open : undefined}
          onClick={() => setOpen(!open)}
          className="flex min-w-0 flex-1 items-center gap-2 py-2 text-start disabled:cursor-default"
        >
          {expandable ? (
            createElement(open ? ChevronDown : ChevronRight, {
              size: 15,
              className: 'shrink-0 text-fg-3 rtl:-scale-x-100',
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
            aria-label={t('agents.section.outputView')}
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
              {t('agents.section.output')}
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
              {t('agents.section.diff')} <span className="text-success">+{change.added}</span>{' '}
              <span className="text-error">−{change.removed}</span>
            </button>
          </span>
        ) : null}
        {section && section.text && !running ? (
          <CopyButton text={section.text} label={t('agents.section.copyOutput')} />
        ) : null}
        <SectionStatus item={item} behind={behind} />
        <SourcesButton sources={sources} />
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
            <DiffView change={change} />
          ) : output ? (
            <Markdown text={output} streaming={running} links={links} />
          ) : running && behind ? (
            <p className="shimmer text-sm">{t('agents.section.queued', { name: behind })}</p>
          ) : running ? (
            <p className="shimmer text-sm">
              {item.agentType === 'web'
                ? t('agents.section.searching')
                : t('agents.section.writing')}
            </p>
          ) : (
            <p className="text-sm text-fg-3">{t('agents.section.noOutput')}</p>
          )}
        </div>
      ) : null}
    </div>
  );
}, sameSectionProps);

/** Une suite de texte ne re-rend que sa section : les autres gardent leur objet section */
function sameSectionProps(
  prev: { item: ThreadItem; provided: unknown; behind?: string },
  next: { item: ThreadItem; provided: unknown; behind?: string },
): boolean {
  const a = prev.item;
  const b = next.item;
  return (
    a.section === b.section &&
    a.title === b.title &&
    a.step === b.step &&
    a.pending === b.pending &&
    a.color === b.color &&
    a.agentType === b.agentType &&
    prev.provided === next.provided &&
    prev.behind === next.behind
  );
}

function RunStatusChip({ run }: { run: RunView }) {
  const t = useT();
  const running = run.status === 'running';
  const elapsed = useElapsed(run.started_at, running);
  if (running) {
    return (
      <span className="flex items-center gap-1.5 rounded-full bg-warning-soft px-2 py-0.5 text-xs text-warning tabular-nums">
        <span className="h-1.5 w-1.5 rounded-full bg-warning pulse-soft" />
        {t(RUN_TONE.running.label)} · {clock(elapsed)}
      </span>
    );
  }
  const tone = RUN_TONE[runTone(run.status, run.status_text)];
  const duration = formatDuration(run.duration_ms ?? undefined);
  return (
    <span className={cn('rounded-full px-2 py-0.5 text-xs', tone.chip)}>
      {t(tone.label)}
      {duration ? ` · ${duration}` : ''}
    </span>
  );
}

function TaskText({ text }: { text: string }) {
  const t = useT();
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
          {expanded ? t('agents.task.collapse') : t('agents.task.expand')}
        </button>
      ) : null}
    </div>
  );
}

/** En-tête du fil, puis ses sections */
function Thread({ run }: { run: RunView }) {
  const t: Translate = useT();
  const summary: RunSummary = useMemo(() => summaryOf(run), [run]);
  const items = useMemo(() => threadItems(run, t), [run, t]);
  const queued = useMemo(() => queuedBehind(run), [run]);
  const provided = useMemo(
    () => providedCode(run.sources, run.task, t),
    [run.sources, run.task, t],
  );
  const plan = run.kind === 'debate' ? debateSummary(run, t) : planSummary(run, t);
  const running = run.status === 'running';
  const preparing = running && !run.sections.length;
  const report = run.schedule?.output_file;
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <RunKindIcon run={summary} size={16} />
            <h3 className="text-[15px] font-semibold text-fg">{run.title}</h3>
            <RunStatusChip run={run} />
            {run.origin !== 'desktop' ? (
              <span className="flex items-center gap-1 rounded-full border border-line px-2 py-0.5 text-xs text-fg-2">
                <OriginIcon origin={run.origin} size={12} />
                {t(ORIGIN_LABEL[run.origin])}
              </span>
            ) : null}
            {report ? (
              <button
                type="button"
                onClick={() => void openFile(report)}
                title={report}
                className="flex items-center gap-1 text-xs text-link hover:underline"
              >
                <FileText size={12} />
                {t('agents.thread.report')}
              </button>
            ) : null}
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
            {t('agents.task.stop')}
          </button>
        ) : null}
      </div>
      {preparing ? (
        <p className="shimmer text-sm">
          {run.attachments.length
            ? t('agents.thread.readingAttachments')
            : run.kind === 'debate'
              ? t('agents.thread.startingDebate')
              : t('agents.thread.startingAgents')}
        </p>
      ) : null}
      {items.map((item) => (
        <Section key={item.key} item={item} provided={provided} behind={queued[item.key]} />
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
  const t = useT();
  const openRunId = useAgents((state) => state.openRunId);
  const run = useAgents((state) => (openRunId ? state.details[openRunId] : undefined));
  if (!openRunId) return null;
  if (!run) return <p className="shimmer text-sm">{t('agents.thread.loading')}</p>;
  return <Thread key={run.id} run={run} />;
}
