/*
 * Fils d'exécution de la page Agents : état tenu à jour par les événements
 * « agents.* » (interfaces/desktop/agents.py). Fonctions pures, testées à part.
 *
 * Règle d'ordre : chaque fil lu en entier (GET /api/agents/runs/{id}) porte le
 * seq de sa lecture ; les événements plus anciens n'y changent rien. Le texte
 * d'une section arrive en suites (offset = longueur avant la suite) : une
 * suite déjà reçue est ignorée, une suite qui laisse un trou (reconnexion) fait
 * relire le fil.
 */

import type { AnyAgentEvent, RunSection, RunSummary, RunView, SectionId } from '../lib/events';

export interface RunsState {
  /** Liste des fils, du plus récent au plus ancien */
  runs: RunSummary[];
  /** Fils lus en entier (ouverts, ou lancés depuis cette fenêtre) */
  details: Record<string, RunView>;
  /** Seq de la dernière lecture complète de chaque fil */
  floors: Record<string, number>;
  /** Fil en cours sur la page Agents */
  active: string | null;
  /** L'exécuteur partagé est occupé (page Agents, mobile, tâche planifiée) */
  busy: boolean;
  /** Fil affiché à droite de la liste */
  openRunId: string | null;
  /** Fils à relire : une suite de texte manque */
  stale: string[];
}

export const EMPTY_RUNS: RunsState = {
  runs: [],
  details: {},
  floors: {},
  active: null,
  busy: false,
  openRunId: null,
  stale: [],
};

/** Ligne de la liste d'un fil complet (Run.summary côté serveur) */
export function summaryOf(run: RunView): RunSummary {
  const first = run.nodes[0];
  const oneLine = run.task.split(/\s+/).join(' ').trim();
  return {
    id: run.id,
    kind: run.kind,
    title: run.title,
    task: oneLine.length <= 160 ? oneLine : `${oneLine.slice(0, 159).trimEnd()}…`,
    status: run.status,
    status_text: run.status_text,
    started_at: run.started_at,
    finished_at: run.finished_at,
    duration_ms: run.duration_ms,
    agent_type: first?.agent_type ?? null,
    color: first?.color ?? null,
    agents: run.nodes.length,
  };
}

function sameId(a: SectionId, b: SectionId): boolean {
  return String(a) === String(b);
}

function newSection(run: RunView, id: SectionId, title = '', color = ''): RunSection {
  const node = run.nodes.find((item) => sameId(item.id, id));
  return {
    id,
    title: title || node?.name || '',
    color: color || node?.color || '',
    agent_type: node?.agent_type ?? null,
    text: '',
    status: 'running',
    started_at: new Date().toISOString(),
    finished_at: null,
  };
}

/** Remplace la section `id` du fil (ou l'ajoute) */
function withSection(
  run: RunView,
  id: SectionId,
  update: (section: RunSection) => RunSection,
): RunView {
  const index = run.sections.findIndex((section) => sameId(section.id, id));
  const sections = [...run.sections];
  if (index < 0) sections.push(update(newSection(run, id)));
  else sections[index] = update(sections[index] as RunSection);
  return { ...run, sections };
}

function finished(run: RunView, status: RunView['status'], statusText: string): RunView {
  const now = new Date();
  const started = Date.parse(run.started_at);
  const nodeStatus = { ...run.node_status };
  for (const [key, value] of Object.entries(nodeStatus)) {
    if (value === 'running') nodeStatus[key] = 'error';
  }
  return {
    ...run,
    status,
    status_text: statusText || run.status_text,
    finished_at: now.toISOString(),
    duration_ms: Number.isNaN(started) ? run.duration_ms : Math.max(0, now.getTime() - started),
    sections: run.sections.map((section) =>
      section.status === 'running' ? { ...section, status: 'error' } : section,
    ),
    node_status: nodeStatus,
  };
}

function withRun(state: RunsState, run: RunView): RunsState {
  const details = { ...state.details, [run.id]: run };
  const ended = run.status !== 'running';
  const runs = state.runs.map((item) => (item.id === run.id ? summaryOf(run) : item));
  return {
    ...state,
    details,
    runs,
    ...(ended && state.active === run.id ? { active: null, busy: false } : {}),
  };
}

function markStale(state: RunsState, id: string): RunsState {
  return state.stale.includes(id) ? state : { ...state, stale: [...state.stale, id] };
}

/** Applique un événement « agents.* » ; renvoie le même état s'il ne change rien */
export function applyAgentEvent(state: RunsState, event: AnyAgentEvent): RunsState {
  if (event.type === 'agents.run_created') {
    const run = event.payload.run;
    return {
      ...state,
      details: { ...state.details, [run.id]: run },
      floors: { ...state.floors, [run.id]: event.seq },
      runs: [summaryOf(run), ...state.runs.filter((item) => item.id !== run.id)],
      active: run.status === 'running' ? run.id : state.active,
      busy: run.status === 'running' ? true : state.busy,
      openRunId: run.id,
    };
  }
  if (event.type === 'agents.runs_changed' || event.type === 'agents.list_changed') return state;

  const id = event.payload.exec_id;
  const run = state.details[id];
  if (!run || event.seq <= (state.floors[id] ?? 0)) return state;

  switch (event.type) {
    case 'agents.agent_exec_start':
      return withRun(state, { ...run, mode: event.payload.mode });
    case 'agents.agent_debate_topic':
      return state;
    case 'agents.agent_section_start': {
      const { section_id: sectionId, title, color } = event.payload;
      return withRun(
        state,
        withSection(run, sectionId, (section) => ({
          ...section,
          title: title || section.title,
          color: color || section.color,
          status: 'running',
        })),
      );
    }
    case 'agents.agent_section_delta': {
      const { section_id: sectionId, text, offset } = event.payload;
      const current = run.sections.find((section) => sameId(section.id, sectionId))?.text ?? '';
      if (offset + text.length <= current.length) return state; // déjà reçue
      if (offset !== current.length) return markStale(state, id); // trou : relire le fil
      return withRun(
        state,
        withSection(run, sectionId, (section) => ({ ...section, text: section.text + text })),
      );
    }
    case 'agents.agent_section_text': {
      const { section_id: sectionId, text } = event.payload;
      return withRun(
        state,
        withSection(run, sectionId, (section) => ({ ...section, text })),
      );
    }
    case 'agents.agent_section_end': {
      const { section_id: sectionId, success } = event.payload;
      return withRun(
        state,
        withSection(run, sectionId, (section) => ({
          ...section,
          status: success ? 'done' : 'error',
          finished_at: new Date().toISOString(),
        })),
      );
    }
    case 'agents.agent_node_status': {
      const { node_id: nodeId, status } = event.payload;
      return withRun(state, {
        ...run,
        node_status: { ...run.node_status, [String(nodeId)]: status },
      });
    }
    case 'agents.agent_exec_end': {
      const { interrupted, success, status_text: statusText } = event.payload;
      const status = interrupted ? 'interrupted' : success ? 'done' : 'error';
      return withRun(state, finished(run, status, statusText));
    }
    case 'agents.agent_exec_error': {
      const message = event.payload.message || 'Erreur';
      return withRun(state, { ...finished(run, 'error', `❌ ${message}`), error: message });
    }
    default:
      return state;
  }
}

/** Fil relu en entier (GET /api/agents/runs/{id}) : il remplace l'ancien */
export function withLoadedRun(state: RunsState, run: RunView, seq: number): RunsState {
  return {
    ...state,
    details: { ...state.details, [run.id]: run },
    floors: { ...state.floors, [run.id]: seq },
    runs: state.runs.map((item) => (item.id === run.id ? summaryOf(run) : item)),
    stale: state.stale.filter((item) => item !== run.id),
  };
}
