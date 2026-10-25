/*
 * Page Agents (interfaces/agents/ de Tk), dans l'ordre de Tk (D32) : la
 * grille des agents, la zone de tâche et ses boutons, le canvas du workflow,
 * puis « Exécutions » à la place de « Résultats » : la liste des fils à
 * gauche, le fil ouvert à droite. Suivent les statistiques et le moniteur de
 * ressources, puis les tâches planifiées.
 *
 * Chargée à la première ouverture de l'onglet (React Flow compris).
 */

import { Trash2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { useT } from '../../i18n';
import { useApp } from '../../stores/app';
import { clearRuns, refreshAgentsPage, useAgents } from '../../stores/agents';
import { loadResources } from '../../stores/resources';
import { loadSchedule } from '../../stores/schedule';
import { AgentGrid } from './AgentGrid';
import { WorkflowCanvas } from './canvas/WorkflowCanvas';
import { RunList } from './runs/RunList';
import { ThreadView } from './runs/ThreadView';
import { ScheduleSection } from './schedule/ScheduleSection';
import { StatsPanel } from './stats/StatsPanel';
import { TaskZone } from './TaskZone';
import { executeWorkflow } from './workflowActions';

/** Accueil de la zone de résultats de Tk, tant qu'aucun fil n'existe */
function Welcome() {
  const t = useT();
  return (
    <div className="rounded-xl border border-dashed border-line px-5 py-6 text-sm leading-relaxed text-fg-2">
      <p className="mb-2 text-fg">{t('agents.welcome.title')}</p>
      <ol className="list-decimal space-y-0.5 ps-5">
        <li>{t('agents.welcome.1')}</li>
        <li>{t('agents.welcome.2')}</li>
        <li>{t('agents.welcome.3')}</li>
      </ol>
      <p className="mt-2">{t('agents.welcome.footer')}</p>
    </div>
  );
}

function Executions() {
  const t = useT();
  const count = useAgents((state) => state.runs.length);
  const runsLoaded = useAgents((state) => state.runsLoaded);
  const active = useAgents((state) => state.active);
  const [confirming, setConfirming] = useState(false);
  return (
    <section aria-labelledby="agents-executions">
      <div className="mb-3 flex items-center gap-2">
        <h2 id="agents-executions" className="text-lg font-semibold text-fg">
          {t('agents.executions.title')}
        </h2>
        {count ? <span className="text-sm text-fg-3 tabular-nums">{count}</span> : null}
        {count > (active ? 1 : 0) ? (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="ms-auto flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-fg-2 hover:bg-hover hover:text-fg"
          >
            <Trash2 size={14} />
            {t('agents.executions.clear')}
          </button>
        ) : null}
      </div>
      {count ? (
        <div className="flex items-start gap-4">
          <aside className="sticky top-4 max-h-[calc(100vh-var(--header-height)-2rem)] w-[310px] shrink-0 overflow-y-auto rounded-xl border border-line bg-bg-2 p-2">
            <RunList />
          </aside>
          <div className="min-w-0 flex-1 rounded-xl border border-line bg-bg p-4">
            <ThreadView />
          </div>
        </div>
      ) : runsLoaded ? (
        <Welcome />
      ) : null}
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={t('agents.executions.clear')}
        message={active ? t('agents.executions.clearActive') : t('agents.executions.clearAll')}
        confirmLabel={t('agents.executions.clearConfirm')}
        danger
        onConfirm={() => void clearRuns()}
      />
    </section>
  );
}

export default function AgentsPage() {
  const t = useT();
  const scroller = useRef<HTMLDivElement>(null);
  const executions = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLDivElement>(null);
  const ready = useApp((state) => state.status?.state === 'ready');

  useEffect(() => {
    if (!ready) return;
    refreshAgentsPage();
    void loadSchedule();
    // Le moniteur de ressources démarre à la première lecture
    void loadResources();
  }, [ready]);

  /** Fait voir `target` si les fils d'exécution sont hors de vue */
  const reveal = (target: HTMLElement | null) => {
    const box = executions.current?.getBoundingClientRect();
    const view = scroller.current?.getBoundingClientRect();
    if (!box || !view || (box.top <= view.bottom - 120 && box.bottom >= view.top + 120)) return;
    const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    target?.scrollIntoView({ block: 'start', behavior: smooth ? 'smooth' : 'auto' });
  };

  const execute = () => {
    void executeWorkflow().then((runId) => {
      // Les sorties s'écrivent sous le canvas : la page descend jusqu'au canvas,
      // qui garde ses statuts visibles au-dessus
      if (runId) reveal(canvas.current);
    });
  };

  return (
    <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto flex max-w-[1760px] flex-col gap-5 px-8 pt-2 pb-10">
        <div>
          <h1 className="text-xl font-semibold text-fg">{t('agents.title')}</h1>
          <p className="text-sm text-fg-2">{t('agents.subtitle')}</p>
        </div>
        <AgentGrid />
        {/* Un débat n'a pas de canvas : la page descend jusqu'à son fil */}
        <TaskZone onExecute={execute} onDebateStarted={() => reveal(executions.current)} />
        <div ref={canvas} className="scroll-mt-4">
          <WorkflowCanvas />
        </div>
        <div ref={executions} className="scroll-mt-4">
          <Executions />
        </div>
        <StatsPanel />
        <ScheduleSection onOpenThread={() => reveal(executions.current)} />
      </div>
    </div>
  );
}
