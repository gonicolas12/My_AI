/*
 * Fichiers de workflow : format JSON de WorkflowCanvas.to_dict (Tk), pour
 * relire les workflows enregistrés avec l'interface Tk et lui rendre les siens.
 *
 *   { "version": "9.1.0",
 *     "nodes": { "0": { agent_type, name, color, icon, x, y, status }, … },
 *     "connections": [ { "from": 0, "to": 1 }, … ],
 *     "zoom": 1.0, "pan_x": 0.0, "pan_y": 0.0 }
 *
 * Comme from_dict de Tk, un chargement renumérote les nœuds à partir de 0.
 * Le format de la PWA mobile (nœuds en liste, avec leur id) est lu aussi.
 */

import type { WorkflowFile } from '../../../lib/api';
import type { NodeStatus } from '../../../lib/events';
import { type Link, MAX_ZOOM, MIN_ZOOM, validLinks } from './graph';

export const WORKFLOW_VERSION = '9.1.0';

export interface WorkflowNode {
  id: number;
  agentType: string;
  name: string;
  color: string;
  /** Émoji de Tk (🐍…), gardé dans le fichier */
  icon: string;
  x: number;
  y: number;
}

export interface WorkflowViewport {
  x: number;
  y: number;
  zoom: number;
}

export interface Workflow {
  nodes: WorkflowNode[];
  links: Link[];
  viewport: WorkflowViewport;
}

/** Workflow → fichier ; `status` : statut affiché de chaque nœud (Tk l'enregistrait aussi) */
export function toWorkflowFile(
  workflow: Workflow,
  status: (id: number) => NodeStatus = () => 'idle',
): WorkflowFile {
  const nodes: WorkflowFile['nodes'] = {};
  for (const node of workflow.nodes) {
    nodes[String(node.id)] = {
      agent_type: node.agentType,
      name: node.name,
      color: node.color,
      icon: node.icon,
      x: node.x,
      y: node.y,
      status: status(node.id),
    };
  }
  return {
    version: WORKFLOW_VERSION,
    nodes,
    connections: workflow.links.map((link) => ({ from: link.from, to: link.to })),
    zoom: workflow.viewport.zoom,
    pan_x: workflow.viewport.x,
    pan_y: workflow.viewport.y,
  };
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function text(value: unknown, fallback = ''): string {
  return typeof value === 'string' ? value : fallback;
}

function number(value: unknown, fallback = 0): number {
  return typeof value === 'number' && Number.isFinite(value) ? value : fallback;
}

/**
 * Fichier → workflow, nœuds renumérotés à partir de 0 ; null si le contenu
 * n'est pas un workflow. Les liens invalides (nœud inconnu, doublon, cycle)
 * sont écartés.
 */
export function fromWorkflowFile(data: unknown): Workflow | null {
  if (!isRecord(data)) return null;
  const rawNodes = data.nodes;
  let entries: [string, unknown][];
  if (isRecord(rawNodes)) entries = Object.entries(rawNodes);
  else if (Array.isArray(rawNodes)) {
    entries = rawNodes.map((item, index) => [String(isRecord(item) ? item.id : index), item]);
  } else return null;

  const idMap = new Map<string, number>();
  const nodes: WorkflowNode[] = [];
  for (const [oldId, raw] of entries) {
    if (!isRecord(raw)) continue;
    const agentType = text(raw.agent_type).trim();
    if (!agentType) continue;
    const id = nodes.length;
    idMap.set(oldId, id);
    nodes.push({
      id,
      agentType,
      name: text(raw.name, agentType),
      color: text(raw.color, '#ff6b47'),
      icon: text(raw.icon, '🤖'),
      x: number(raw.x),
      y: number(raw.y),
    });
  }
  if (!nodes.length && entries.length) return null;

  const rawLinks = Array.isArray(data.connections) ? data.connections : [];
  const links: Link[] = [];
  for (const raw of rawLinks) {
    if (!isRecord(raw)) continue;
    const from = idMap.get(String(raw.from));
    const to = idMap.get(String(raw.to));
    if (from !== undefined && to !== undefined) links.push({ from, to });
  }

  const zoom = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, number(data.zoom, 1)));
  return {
    nodes,
    links: validLinks(links, new Set(nodes.map((node) => node.id))),
    viewport: { x: number(data.pan_x), y: number(data.pan_y), zoom },
  };
}
