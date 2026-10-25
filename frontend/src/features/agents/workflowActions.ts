/*
 * Actions de la page Agents qui touchent au canvas : exécuter le workflow,
 * l'enregistrer, le charger, l'exporter (task_input.py, workflow.py de Tk).
 *
 * Dans la fenêtre de l'appli, les fichiers se choisissent dans les dialogues
 * du système ; dans un navigateur (repli, --dev), l'enregistrement et l'export
 * vont dans outputs/, et un workflow se charge par le sélecteur de la page.
 */

import { t } from '../../i18n';
import { api } from '../../lib/api';
import { shell } from '../../lib/shell';
import { notify } from '../../stores/app';
import { errorText, useAgents } from '../../stores/agents';
import { currentWorkflow, loadWorkflow, setCanvasRun, useWorkflow } from './canvas/workflowStore';
import { fromWorkflowFile, toWorkflowFile } from './canvas/workflowFile';

/** Statut de chaque nœud à la dernière exécution lancée d'ici */
function nodeStatus() {
  const runId = useWorkflow.getState().runId;
  const status = runId ? useAgents.getState().details[runId]?.node_status : undefined;
  return (id: number) => status?.[String(id)] ?? 'idle';
}

/**
 * « Exécuter » : agent seul ou workflow du canvas, avec la tâche et ses
 * pièces jointes. Les pièces jointes partent avec la tâche, comme dans Tk.
 * Renvoie l'identifiant du fil, ou null si rien n'est lancé.
 */
export async function executeWorkflow(): Promise<string | null> {
  const { task, attachments, starting, active } = useAgents.getState();
  const workflow = currentWorkflow();
  if (starting) return null;
  if (active) {
    // Messages de Tk (execution.py), en notifications plutôt qu'en boîtes du système
    notify('warning', t('agents.workflow.busy'));
    return null;
  }
  if (!workflow.nodes.length) {
    notify('warning', t('agents.workflow.noAgent'));
    return null;
  }
  if (!task.trim()) {
    notify('warning', t('agents.workflow.emptyTask'));
    return null;
  }
  useAgents.setState({ starting: true });
  try {
    const { run_id: runId } = await api.startRun({
      task,
      nodes: workflow.nodes.map((node) => ({
        id: node.id,
        agent_type: node.agentType,
        name: node.name,
        color: node.color,
        icon: node.icon,
        x: node.x,
        y: node.y,
      })),
      connections: workflow.links,
      attachments: attachments.map((item) => ({ path: item.path, type: item.type })),
    });
    setCanvasRun(runId);
    useAgents.setState({ attachments: [] });
    return runId;
  } catch (error) {
    notify('warning', errorText(error));
    return null;
  } finally {
    useAgents.setState({ starting: false });
  }
}

/** « Enregistrer » : le workflow en JSON, au format de Tk */
export async function saveWorkflowFile(): Promise<void> {
  const file = toWorkflowFile(currentWorkflow(), nodeStatus());
  let path: string | null = null;
  if (shell.isDesktop()) {
    path = await shell.saveFile('workflow.json', 'json');
    if (!path) return;
  }
  try {
    const saved = await api.saveWorkflow(path, file);
    if (!path) notify('info', t('agents.workflow.savedIn', { path: saved.path }));
  } catch (error) {
    notify('error', errorText(error));
  }
}

/** Workflow lu (fichier de Tk, de la fenêtre ou de la PWA) : il remplace le canvas */
export function applyWorkflowData(data: unknown): void {
  const workflow = fromWorkflowFile(data);
  if (!workflow) {
    notify('error', t('agents.workflow.loadError'));
    return;
  }
  loadWorkflow(workflow);
  notify('success', t('agents.workflow.loaded'));
}

/** « Charger » dans la fenêtre de l'appli ; renvoie faux dans un navigateur (sélecteur de la page) */
export async function loadWorkflowFile(): Promise<boolean> {
  if (!shell.isDesktop()) return false;
  const path = await shell.pickWorkflow();
  if (!path) return true;
  try {
    const { workflow } = await api.readWorkflow(path);
    applyWorkflowData(workflow);
  } catch (error) {
    notify('error', errorText(error));
  }
  return true;
}

/** Fichier choisi dans un navigateur */
export async function loadWorkflowBlob(file: File): Promise<void> {
  try {
    applyWorkflowData(JSON.parse(await file.text()) as unknown);
  } catch {
    notify('error', t('agents.workflow.loadError'));
  }
}

/** « Exporter » : Markdown avec la tâche, les agents et leurs réponses (D11) */
export async function exportWorkflowFile(): Promise<void> {
  const file = toWorkflowFile(currentWorkflow(), nodeStatus());
  let path: string | null = null;
  if (shell.isDesktop()) {
    path = await shell.saveFile('workflow_export.md', 'markdown');
    if (!path) return;
  }
  try {
    // Dernière exécution lancée du canvas ; après un redémarrage, le fil le plus récent
    const runId =
      useWorkflow.getState().runId ??
      useAgents.getState().runs.find((run) => run.kind !== 'debate')?.id ??
      null;
    const saved = await api.exportWorkflow(path, file, runId);
    if (!path) notify('info', t('agents.workflow.exportedIn', { path: saved.path }));
  } catch (error) {
    notify('error', errorText(error));
  }
}
