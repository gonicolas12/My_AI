/*
 * Page Agents : agents de la grille, zone de tâche, fils d'exécution
 * (interfaces/desktop/agents.py).
 *
 * Les fils sont tenus à jour par les événements « agents.* »
 * (agentsReducer.ts) ; les lectures complètes se font à l'ouverture de la
 * page, d'un fil, et après une reconnexion. Le canvas du workflow a son
 * propre store (features/agents/canvas/workflowStore.ts), chargé avec la page.
 */

import { create } from 'zustand';

import { type AgentStats, api } from '../lib/api';
import type { AgentInfo, AnyAgentEvent, RunAttachment, RunOrigin } from '../lib/events';
import { notify } from './app';
import { applyAgentEvent, EMPTY_RUNS, type RunsState, withLoadedRun } from './agentsReducer';

/** Pièce jointe de la zone de tâche, lue par l'exécuteur au lancement (comme Tk) */
export interface TaskAttachment extends RunAttachment {
  id: string;
}

interface AgentsState extends RunsState {
  builtin: AgentInfo[];
  custom: AgentInfo[];
  /** Liste des agents lue au moins une fois */
  loaded: boolean;
  /** Fils lus au moins une fois */
  runsLoaded: boolean;
  /** Tâche en cours de saisie : elle survit aux changements d'onglet */
  task: string;
  attachments: TaskAttachment[];
  /** Exécution demandée, réponse du serveur attendue */
  starting: boolean;
  /** Statistiques sur les fils gardés (relues avec la liste des fils) */
  stats: AgentStats;
}

const initialState: AgentsState = {
  ...EMPTY_RUNS,
  builtin: [],
  custom: [],
  loaded: false,
  runsLoaded: false,
  task: '',
  attachments: [],
  starting: false,
  stats: { tasks: 0, agents: 0, success_rate: null },
};

export const useAgents = create<AgentsState>()(() => initialState);

export function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

// ── Lectures ────────────────────────────────────────────────────────────────

export async function loadAgents(): Promise<void> {
  try {
    const list = await api.agents();
    useAgents.setState({ builtin: list.builtin, custom: list.custom, loaded: true });
  } catch {
    // moteur au démarrage ou serveur injoignable : la reconnexion relira la liste
  }
}

/** Fil lu en entier (ouverture, trou dans le texte, reconnexion) */
export async function loadRun(id: string): Promise<void> {
  try {
    const { run, seq } = await api.agentRun(id);
    useAgents.setState((state) => withLoadedRun(state, run, seq));
  } catch {
    useAgents.setState((state) => ({ stale: state.stale.filter((item) => item !== id) }));
  }
}

/** Liste des fils ; le fil ouvert (sinon le plus récent) est relu en entier */
export async function loadRuns(): Promise<void> {
  try {
    const { runs, active, busy, stats } = await api.agentRuns();
    const state = useAgents.getState();
    const known = new Set(runs.map((run) => run.id));
    const openRunId =
      state.openRunId && known.has(state.openRunId) ? state.openRunId : (runs[0]?.id ?? null);
    useAgents.setState({ runs, active, busy, stats, openRunId, runsLoaded: true });
    if (openRunId) await loadRun(openRunId);
    if (active && active !== openRunId) await loadRun(active);
  } catch {
    // relue à la reconnexion
  }
}

/** Tout relire : page ouverte, ou reconnexion après une coupure */
export function refreshAgentsPage(): void {
  void loadAgents();
  void loadRuns();
}

let runsTimer: ReturnType<typeof setTimeout> | null = null;
let listTimer: ReturnType<typeof setTimeout> | null = null;

/** Applique un lot d'événements « agents.* » (un seul rendu par lot) */
export function applyAgentEvents(events: AnyAgentEvent[]): void {
  if (!events.length) return;
  useAgents.setState((state) => events.reduce<RunsState>(applyAgentEvent, state));
  // Relectures regroupées : plusieurs changements, une requête
  if (events.some((event) => event.type === 'agents.runs_changed')) {
    if (runsTimer) clearTimeout(runsTimer);
    runsTimer = setTimeout(() => {
      runsTimer = null;
      void loadRuns();
    }, 250);
  }
  if (events.some((event) => event.type === 'agents.list_changed')) {
    if (listTimer) clearTimeout(listTimer);
    listTimer = setTimeout(() => {
      listTimer = null;
      void loadAgents();
    }, 150);
  }
  for (const id of useAgents.getState().stale) void loadRun(id);
}

// ── Fils ────────────────────────────────────────────────────────────────────

export function openRun(id: string): void {
  useAgents.setState({ openRunId: id });
  if (!useAgents.getState().details[id]) void loadRun(id);
}

/** Arrête le fil en cours (Arrêter, Échap) */
export async function stopAgentsRun(): Promise<void> {
  const active = useAgents.getState().active;
  if (!active) return;
  try {
    await api.stopRun(active);
  } catch (error) {
    notify('error', errorText(error));
  }
}

/** Origine du fil en cours : la page, le téléphone ou une tâche planifiée */
export function activeOrigin(): RunOrigin | null {
  const { active, details, runs } = useAgents.getState();
  if (!active) return null;
  return details[active]?.origin ?? runs.find((run) => run.id === active)?.origin ?? 'desktop';
}

/** Lance un débat (dialogue « Mode Débat ») ; l'erreur du serveur remonte au dialogue */
export async function startDebate(
  agentA: string,
  agentB: string,
  topic: string,
  rounds: number,
): Promise<string> {
  const { run_id: runId } = await api.startDebate(agentA, agentB, topic, rounds);
  return runId;
}

export async function deleteRun(id: string): Promise<void> {
  try {
    await api.deleteRun(id);
    useAgents.setState((state) => {
      const runs = state.runs.filter((run) => run.id !== id);
      const details = { ...state.details };
      delete details[id];
      const openRunId = state.openRunId === id ? (runs[0]?.id ?? null) : state.openRunId;
      return { runs, details, openRunId };
    });
    const open = useAgents.getState().openRunId;
    if (open && !useAgents.getState().details[open]) void loadRun(open);
  } catch (error) {
    notify('error', errorText(error));
  }
}

export async function clearRuns(): Promise<void> {
  try {
    await api.clearRuns();
    await loadRuns();
  } catch (error) {
    notify('error', errorText(error));
  }
}

// ── Zone de tâche ───────────────────────────────────────────────────────────

export function setTask(task: string): void {
  useAgents.setState({ task });
}

let attachmentId = 0;

function addAttachments(items: RunAttachment[], refused: string[]): void {
  for (const message of refused) notify('error', message);
  if (!items.length) return;
  useAgents.setState((state) => {
    const known = new Set(state.attachments.map((item) => item.path.toLowerCase()));
    const added = items
      .filter((item) => !known.has(item.path.toLowerCase()))
      .map((item) => ({ ...item, id: `att-${++attachmentId}` }));
    return { attachments: [...state.attachments, ...added] };
  });
}

/** Fichiers choisis (dialogue) ou déposés, par leur chemin ; un dossier joint ses fichiers */
export async function addTaskPaths(paths: string[]): Promise<void> {
  if (!paths.length) return;
  try {
    const { attachments, refused } = await api.agentAttachments(paths);
    addAttachments(attachments, refused);
  } catch (error) {
    notify('error', errorText(error));
  }
}

/** Fichiers sans chemin (navigateur, image collée) : leur contenu part au serveur */
export async function uploadTaskFiles(files: File[], name?: string): Promise<void> {
  for (const file of files) {
    try {
      const { attachments, refused } = await api.uploadAgentAttachment(file, name ?? file.name);
      addAttachments(attachments, refused);
    } catch (error) {
      notify('error', errorText(error));
    }
  }
}

export function removeTaskAttachment(id: string): void {
  useAgents.setState((state) => ({
    attachments: state.attachments.filter((item) => item.id !== id),
  }));
}

// ── Agents personnalisés ────────────────────────────────────────────────────

/** Crée un agent ; l'erreur du serveur remonte au dialogue */
export async function createAgent(name: string, role: string): Promise<AgentInfo> {
  const { agent } = await api.createAgent(name, role);
  await loadAgents();
  return agent;
}

export async function editAgent(key: string, name: string, role: string): Promise<AgentInfo> {
  const { agent } = await api.editAgent(key, name, role);
  await loadAgents();
  return agent;
}

export async function deleteAgent(key: string): Promise<boolean> {
  try {
    await api.deleteAgent(key);
    await loadAgents();
    return true;
  } catch (error) {
    notify('error', errorText(error));
    return false;
  }
}

/** Réservé aux tests */
export function resetAgents(): void {
  useAgents.setState(initialState, true);
}
