import { describe, expect, it } from 'vitest';

import { autoPosition, canLink, snap, validLinks } from './graph';
import { fromWorkflowFile, toWorkflowFile } from './workflowFile';

/** Fichier enregistré par l'interface Tk (WorkflowCanvas.to_dict) */
const TK_FILE = {
  version: '8.1.0',
  nodes: {
    '4': {
      agent_type: 'planner',
      name: 'PlannerAgent',
      color: '#06b6d4',
      icon: '📋',
      x: 75,
      y: 100,
      status: 'done',
    },
    '7': {
      agent_type: 'code',
      name: 'CodeAgent',
      color: '#3b82f6',
      icon: '🐍',
      x: 375,
      y: 25,
      status: 'idle',
    },
    '9': {
      agent_type: 'security',
      name: 'SecurityAgent',
      color: '#ec4899',
      icon: '🛡',
      x: 375,
      y: 200,
      status: 'error',
    },
  },
  connections: [
    { from: 4, to: 7 },
    { from: 4, to: 9 },
    { from: 4, to: 12 }, // nœud inconnu
    { from: 7, to: 4 }, // cycle
  ],
  zoom: 1.5,
  pan_x: -20,
  pan_y: 10,
};

describe('fichiers de workflow (format de Tk)', () => {
  it('lit un fichier de Tk, nœuds renumérotés depuis 0 comme from_dict', () => {
    const workflow = fromWorkflowFile(TK_FILE)!;
    expect(workflow.nodes.map((node) => [node.id, node.agentType, node.x, node.y])).toEqual([
      [0, 'planner', 75, 100],
      [1, 'code', 375, 25],
      [2, 'security', 375, 200],
    ]);
    // Liens renumérotés ; lien vers un nœud inconnu et cycle écartés
    expect(workflow.links).toEqual([
      { from: 0, to: 1 },
      { from: 0, to: 2 },
    ]);
    expect(workflow.viewport).toEqual({ x: -20, y: 10, zoom: 1.5 });
  });

  it('écrit le format de Tk, dans son ordre, avec le statut de chaque nœud', () => {
    const workflow = fromWorkflowFile(TK_FILE)!;
    const file = toWorkflowFile(workflow, (id) => (id === 0 ? 'done' : 'idle'));
    expect(Object.keys(file)).toEqual([
      'version',
      'nodes',
      'connections',
      'zoom',
      'pan_x',
      'pan_y',
    ]);
    expect(Object.keys(file.nodes['0']!)).toEqual([
      'agent_type',
      'name',
      'color',
      'icon',
      'x',
      'y',
      'status',
    ]);
    expect(file.nodes['0']).toMatchObject({ icon: '📋', status: 'done' });
    expect(file.nodes['1']!.status).toBe('idle');
    expect(fromWorkflowFile(file)).toEqual(workflow);
  });

  it('lit aussi le format de la PWA (nœuds en liste)', () => {
    const workflow = fromWorkflowFile({
      nodes: [
        { id: 3, agent_type: 'web', name: 'WebAgent', color: '#10b981', x: 10, y: 20 },
        { id: 5, agent_type: 'analyst', name: 'AnalystAgent', color: '#8b5cf6', x: 300, y: 20 },
      ],
      connections: [{ from: 3, to: 5 }],
    })!;
    expect(workflow.nodes.map((node) => node.agentType)).toEqual(['web', 'analyst']);
    expect(workflow.links).toEqual([{ from: 0, to: 1 }]);
    expect(workflow.viewport).toEqual({ x: 0, y: 0, zoom: 1 });
  });

  it('refuse ce qui n’est pas un workflow, borne le zoom de Tk', () => {
    expect(fromWorkflowFile(null)).toBeNull();
    expect(fromWorkflowFile([1, 2])).toBeNull();
    expect(fromWorkflowFile({ nodes: 'x' })).toBeNull();
    expect(fromWorkflowFile({ nodes: { '0': { name: 'sans type' } } })).toBeNull();
    expect(fromWorkflowFile({ nodes: {}, zoom: 9 })!.viewport.zoom).toBe(3);
    expect(fromWorkflowFile({ nodes: {}, zoom: 0.01 })!.viewport.zoom).toBe(0.3);
  });
});

describe('règles du graphe', () => {
  it('refuse boucle, doublon, aller-retour et cycle plus long', () => {
    const links = [
      { from: 0, to: 1 },
      { from: 1, to: 2 },
    ];
    expect(canLink(links, 2, 2)).toBe(false);
    expect(canLink(links, 0, 1)).toBe(false);
    expect(canLink(links, 1, 0)).toBe(false);
    expect(canLink(links, 2, 0)).toBe(false);
    expect(canLink(links, 0, 2)).toBe(true);
    expect(canLink(links, 2, 3)).toBe(true);
  });

  it('garde les liens valides d’un fichier, dans leur ordre', () => {
    const kept = validLinks(
      [
        { from: 0, to: 1 },
        { from: 0, to: 1 },
        { from: 1, to: 0 },
        { from: 1, to: 9 },
        { from: 1, to: 2 },
      ],
      new Set([0, 1, 2]),
    );
    expect(kept).toEqual([
      { from: 0, to: 1 },
      { from: 1, to: 2 },
    ]);
  });

  it('place en cascade sur la grille, quatre nœuds par ligne', () => {
    expect(snap(37)).toBe(25);
    expect(snap(38)).toBe(50);
    expect(autoPosition(0)).toEqual({ x: 75, y: 50 });
    expect(autoPosition(3)).toEqual({ x: 975, y: 50 });
    expect(autoPosition(4)).toEqual({ x: 75, y: 175 });
  });
});
