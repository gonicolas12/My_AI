/*
 * Page Agents (interfaces/agents/ de Tk), dans l'ordre de Tk (D32) : la
 * grille des agents, la zone de tâche et ses boutons, le canvas du workflow,
 * puis « Exécutions » à la place de « Résultats » : la liste des fils à
 * gauche, le fil ouvert à droite. Statistiques et tâches planifiées viennent
 * en phase 4b.
 *
 * Chargée à la première ouverture de l'onglet (React Flow compris).
 */

import { Trash2 } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { useApp } from '../../stores/app';
import { clearRuns, refreshAgentsPage, useAgents } from '../../stores/agents';
import { AgentGrid } from './AgentGrid';
import { WorkflowCanvas } from './canvas/WorkflowCanvas';
import { RunList } from './runs/RunList';
import { ThreadView } from './runs/ThreadView';
import { TaskZone } from './TaskZone';
import { executeWorkflow } from './workflowActions';

/** Accueil de la zone de résultats de Tk, tant qu'aucun fil n'existe */
function Welcome() {
  return (
    <div className="rounded-xl border border-dashed border-line px-5 py-6 text-sm leading-relaxed text-fg-2">
      <p className="mb-2 text-fg">Bienvenue dans le système d’agents spécialisés !</p>
      <ol className="list-decimal space-y-0.5 pl-5">
        <li>Décrivez votre tâche</li>
        <li>Configurez votre workflow : glissez des agents sur le canvas, reliez leurs ports</li>
        <li>Cliquez sur « Exécuter »</li>
      </ol>
      <p className="mt-2">Les résultats apparaîtront ici en temps réel, un fil par exécution.</p>
    </div>
  );
}

function Executions() {
  const count = useAgents((state) => state.runs.length);
  const runsLoaded = useAgents((state) => state.runsLoaded);
  const active = useAgents((state) => state.active);
  const [confirming, setConfirming] = useState(false);
  return (
    <section aria-labelledby="agents-executions">
      <div className="mb-3 flex items-center gap-2">
        <h2 id="agents-executions" className="text-lg font-semibold text-fg">
          Exécutions
        </h2>
        {count ? <span className="text-sm text-fg-3 tabular-nums">{count}</span> : null}
        {count > (active ? 1 : 0) ? (
          <button
            type="button"
            onClick={() => setConfirming(true)}
            className="ml-auto flex items-center gap-1.5 rounded-md px-2 py-1 text-sm text-fg-2 hover:bg-hover hover:text-fg"
          >
            <Trash2 size={14} />
            Effacer l’historique
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
        title="Effacer l’historique"
        message={
          active
            ? 'Les fils terminés seront supprimés ; le fil en cours reste.'
            : 'Tous les fils d’exécution seront supprimés.'
        }
        confirmLabel="Effacer"
        danger
        onConfirm={() => void clearRuns()}
      />
    </section>
  );
}

export default function AgentsPage() {
  const scroller = useRef<HTMLDivElement>(null);
  const executions = useRef<HTMLDivElement>(null);
  const canvas = useRef<HTMLDivElement>(null);
  const ready = useApp((state) => state.status?.state === 'ready');

  useEffect(() => {
    if (ready) refreshAgentsPage();
  }, [ready]);

  const execute = () => {
    void executeWorkflow().then((runId) => {
      if (!runId) return;
      // Les sorties s'écrivent sous le canvas : si elles sont hors de vue, la page
      // descend jusqu'au canvas, qui garde ses statuts visibles au-dessus
      const box = executions.current?.getBoundingClientRect();
      const view = scroller.current?.getBoundingClientRect();
      if (box && view && box.top > view.bottom - 120) {
        const smooth = !window.matchMedia('(prefers-reduced-motion: reduce)').matches;
        canvas.current?.scrollIntoView({ block: 'start', behavior: smooth ? 'smooth' : 'auto' });
      }
    });
  };

  return (
    <div ref={scroller} className="min-h-0 flex-1 overflow-y-auto">
      <div className="mx-auto flex max-w-[1760px] flex-col gap-5 px-8 pt-2 pb-10">
        <div>
          <h1 className="text-xl font-semibold text-fg">Agents IA spécialisés</h1>
          <p className="text-sm text-fg-2">
            Choisissez un agent selon la tâche, ou composez un workflow : glissez les agents sur le
            canvas et reliez-les.
          </p>
        </div>
        <AgentGrid />
        <TaskZone onExecute={execute} />
        <div ref={canvas} className="scroll-mt-4">
          <WorkflowCanvas />
        </div>
        <div ref={executions}>
          <Executions />
        </div>
      </div>
    </div>
  );
}
