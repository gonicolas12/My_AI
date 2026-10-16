/*
 * Canvas du workflow : nœuds, liens, vue (zoom, déplacement) et grille.
 *
 * Gardé dans un store pour survivre aux changements d'onglet (la page Agents
 * est démontée quand on passe au Chat), comme le canvas de Tk restait en
 * mémoire. Les identifiants des nœuds sont des entiers, comme dans Tk et ses
 * fichiers de workflow ; React Flow les reçoit en texte.
 */

import {
  applyEdgeChanges,
  applyNodeChanges,
  type Edge,
  type EdgeChange,
  type Node,
  type NodeChange,
  type Viewport,
} from '@xyflow/react';
import { create } from 'zustand';

import type { AgentInfo, NodeStatus } from '../../../lib/events';
import { agentColor, agentEmoji } from '../agentMeta';
import { autoPosition, canLink, type Link, snap } from './graph';
import type { Workflow, WorkflowNode } from './workflowFile';

export interface AgentNodeData extends Record<string, unknown> {
  agentType: string;
  name: string;
  color: string;
  /** Émoji de Tk, gardé pour les fichiers de workflow */
  icon: string;
  /** Statut de la dernière exécution lancée d'ici (posé à l'affichage) */
  status?: NodeStatus;
  /** En cours, mais le modèle répond d'abord à cet agent (posé à l'affichage) */
  queuedBehind?: string;
}

export type AgentFlowNode = Node<AgentNodeData, 'agent'>;

export interface AgentEdgeData extends Record<string, unknown> {
  /** Couleur d'affichage du nœud source (liens de Tk) : jeton d'un agent intégré */
  color: string;
  /** Le nœud cible est en cours : le lien s'anime (posé à l'affichage) */
  running?: boolean;
}

export type AgentFlowEdge = Edge<AgentEdgeData, 'agent'>;

interface WorkflowState {
  nodes: AgentFlowNode[];
  edges: AgentFlowEdge[];
  nextId: number;
  viewport: Viewport;
  grid: boolean;
  /** Fil dont le canvas montre les statuts : la dernière exécution lancée d'ici */
  runId: string | null;
}

const initialState: WorkflowState = {
  nodes: [],
  edges: [],
  nextId: 0,
  viewport: { x: 0, y: 0, zoom: 1 },
  grid: true,
  runId: null,
};

export const useWorkflow = create<WorkflowState>()(() => initialState);

export function nodeId(node: { id: string }): number {
  return Number(node.id);
}

function edgeOf(from: number, to: number, color: string): AgentFlowEdge {
  return {
    id: `e${from}-${to}`,
    source: String(from),
    target: String(to),
    type: 'agent',
    data: { color },
  };
}

function flowNode(node: WorkflowNode): AgentFlowNode {
  return {
    id: String(node.id),
    type: 'agent',
    position: { x: node.x, y: node.y },
    data: { agentType: node.agentType, name: node.name, color: node.color, icon: node.icon },
  };
}

/** Ajoute un agent ; sans position, placement en cascade (add_node de Tk) */
export function addAgentNode(agent: AgentInfo, position?: { x: number; y: number }): void {
  useWorkflow.setState((state) => {
    const id = state.nextId;
    const where = position
      ? { x: snap(position.x), y: snap(position.y) }
      : autoPosition(state.nodes.length);
    const node = flowNode({
      id,
      agentType: agent.key,
      name: agent.name,
      color: agent.color,
      icon: agent.custom ? '🤖' : agentEmoji(agent.key),
      ...where,
    });
    return { nodes: [...state.nodes, node], nextId: id + 1 };
  });
}

export function removeNode(id: string): void {
  useWorkflow.setState((state) => ({
    nodes: state.nodes.filter((node) => node.id !== id),
    edges: state.edges.filter((edge) => edge.source !== id && edge.target !== id),
  }));
}

/** Agent personnalisé supprimé : ses nœuds quittent le canvas */
export function removeAgentNodes(agentType: string): void {
  const ids = useWorkflow
    .getState()
    .nodes.filter((node) => node.data.agentType === agentType)
    .map((node) => node.id);
  for (const id of ids) removeNode(id);
}

export function removeEdge(id: string): void {
  useWorkflow.setState((state) => ({ edges: state.edges.filter((edge) => edge.id !== id) }));
}

export function onNodesChange(changes: NodeChange<AgentFlowNode>[]): void {
  useWorkflow.setState((state) => {
    const nodes = applyNodeChanges(changes, state.nodes);
    const kept = new Set(nodes.map((node) => node.id));
    // Nœud supprimé (Suppr) : ses liens partent avec lui
    const edges = state.edges.filter((edge) => kept.has(edge.source) && kept.has(edge.target));
    return { nodes, edges };
  });
}

export function onEdgesChange(changes: EdgeChange<AgentFlowEdge>[]): void {
  useWorkflow.setState((state) => ({ edges: applyEdgeChanges(changes, state.edges) }));
}

export function linksOf(edges: AgentFlowEdge[]): Link[] {
  return edges.map((edge) => ({ from: Number(edge.source), to: Number(edge.target) }));
}

/** Lien proposé par un glisser de port à port : accepté selon les règles de graph.ts */
export function isValidLink(source: string | null, target: string | null): boolean {
  if (source === null || target === null) return false;
  return canLink(linksOf(useWorkflow.getState().edges), Number(source), Number(target));
}

export function connect(source: string | null, target: string | null): void {
  if (!isValidLink(source, target)) return;
  useWorkflow.setState((state) => {
    const from = state.nodes.find((node) => node.id === source);
    if (!from) return {};
    const color = agentColor(from.data.agentType, from.data.color);
    return { edges: [...state.edges, edgeOf(Number(source), Number(target), color)] };
  });
}

/** « Vider » : canvas vide, numérotation reprise à 0 (clear_workflow de Tk) */
export function clearWorkflow(): void {
  useWorkflow.setState({ nodes: [], edges: [], nextId: 0, runId: null });
}

export function setViewport(viewport: Viewport): void {
  useWorkflow.setState({ viewport });
}

export function toggleGrid(): void {
  useWorkflow.setState((state) => ({ grid: !state.grid }));
}

export function setCanvasRun(runId: string | null): void {
  useWorkflow.setState({ runId });
}

/** Workflow courant, pour l'enregistrer ou le lancer */
export function currentWorkflow(): Workflow {
  const { nodes, edges, viewport } = useWorkflow.getState();
  return {
    nodes: nodes.map((node) => ({
      id: nodeId(node),
      agentType: node.data.agentType,
      name: node.data.name,
      color: node.data.color,
      icon: node.data.icon,
      x: node.position.x,
      y: node.position.y,
    })),
    links: linksOf(edges),
    viewport,
  };
}

/** Workflow chargé (fichier de Tk ou de la fenêtre) : il remplace le canvas */
export function loadWorkflow(workflow: Workflow): void {
  const colors = new Map(
    workflow.nodes.map((node) => [node.id, agentColor(node.agentType, node.color)]),
  );
  useWorkflow.setState({
    nodes: workflow.nodes.map(flowNode),
    edges: workflow.links.map((link) =>
      edgeOf(link.from, link.to, colors.get(link.from) ?? 'var(--accent)'),
    ),
    nextId: workflow.nodes.reduce((max, node) => Math.max(max, node.id + 1), 0),
    viewport: workflow.viewport,
    runId: null,
  });
}

/** Réservé aux tests */
export function resetWorkflow(): void {
  useWorkflow.setState(initialState, true);
}
