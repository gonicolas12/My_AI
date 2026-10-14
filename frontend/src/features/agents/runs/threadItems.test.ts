import { describe, expect, it } from 'vitest';

import type { RunSection, RunView } from '../../../lib/events';
import { runTone } from '../agentMeta';
import { planSummary, queuedBehind, threadItems } from './threadItems';

const NODES = [
  { id: 0, agent_type: 'planner', name: 'PlannerAgent', color: '#06b6d4' },
  { id: 1, agent_type: 'code', name: 'CodeAgent', color: '#3b82f6' },
  { id: 2, agent_type: 'security', name: 'SecurityAgent', color: '#ec4899' },
  { id: 3, agent_type: 'debug', name: 'DebugAgent', color: '#ef4444' },
  { id: 4, agent_type: 'web', name: 'WebAgent', color: '#10b981' },
];

function section(id: number, title: string): RunSection {
  return {
    id,
    title,
    color: '',
    agent_type: null,
    text: 'sortie',
    status: 'done',
    started_at: null,
    finished_at: null,
  };
}

function dag(overrides: Partial<RunView> = {}): RunView {
  return {
    id: 'exec_1',
    kind: 'workflow',
    title: 'Workflow · 5 agents',
    task: 'Tâche',
    attachments: [],
    sources: [],
    nodes: NODES,
    connections: [],
    plan: { mode: 'dag', steps: [[0], [1, 2], [3]], isolated: [4] },
    mode: 'dag',
    status: 'running',
    status_text: '',
    error: null,
    started_at: '2026-10-14T14:02:00',
    finished_at: null,
    duration_ms: null,
    sections: [section(0, 'PlannerAgent'), section(4, 'Agent isolé : WebAgent')],
    node_status: {},
    ...overrides,
  };
}

describe('contenu d’un fil', () => {
  it('suit le plan : étapes, parallèle, isolés, agents en attente', () => {
    const items = threadItems(dag());
    expect(items.map((item) => [item.title, item.step, item.pending])).toEqual([
      ['PlannerAgent', 'Étape 1/3', null],
      ['CodeAgent', 'Étape 2/3 · parallèle', 'waiting'],
      ['SecurityAgent', 'Étape 2/3 · parallèle', 'waiting'],
      ['DebugAgent', 'Étape 3/3', 'waiting'],
      ['Agent isolé : WebAgent', 'Agent isolé', null],
    ]);
    expect(items[1]!.agentType).toBe('code');
  });

  it('un fil terminé marque les agents jamais lancés', () => {
    const items = threadItems(dag({ status: 'interrupted' }));
    expect(items.filter((item) => item.pending === 'skipped').map((item) => item.title)).toEqual([
      'CodeAgent',
      'SecurityAgent',
      'DebugAgent',
    ]);
  });

  it('agent seul : pas d’étape ; agents sans lien : en parallèle', () => {
    const single = dag({
      kind: 'agent',
      nodes: [NODES[1]!],
      plan: { mode: 'single', steps: [[1]], isolated: [] },
      sections: [],
    });
    expect(threadItems(single).map((item) => item.step)).toEqual(['']);
    expect(planSummary(single)).toBe('');
    const parallel = dag({
      plan: { mode: 'parallel', steps: [[1, 2]], isolated: [] },
      sections: [],
    });
    expect(threadItems(parallel).map((item) => item.step)).toEqual([
      'En parallèle',
      'En parallèle',
    ]);
    expect(planSummary(parallel)).toBe('En parallèle : CodeAgent, SecurityAgent');
  });

  it('résume le plan en une ligne', () => {
    expect(planSummary(dag())).toBe(
      'Étape 1 : PlannerAgent · Étape 2, en parallèle : CodeAgent, SecurityAgent · ' +
        'Étape 3 : DebugAgent · Agent isolé : WebAgent',
    );
  });
});

describe('agents qui attendent leur tour', () => {
  const running = (id: number, title: string, text: string): RunSection => ({
    ...section(id, title),
    text,
    status: 'running',
  });

  it('en parallèle, l’agent sans texte attend celui qui écrit', () => {
    const run = dag({
      sections: [
        section(0, 'PlannerAgent'),
        running(1, 'CodeAgent', '# Code'),
        running(2, 'SecurityAgent', ''),
      ],
    });
    expect(queuedBehind(run)).toEqual({ '2': 'CodeAgent' });
  });

  it('personne n’attend tant qu’aucun agent n’écrit, ni après sa sortie', () => {
    const reading = dag({
      sections: [
        section(0, 'PlannerAgent'),
        running(1, 'CodeAgent', ''),
        running(2, 'SecurityAgent', ''),
      ],
    });
    expect(queuedBehind(reading)).toEqual({});
    const after = dag({
      sections: [
        section(0, 'PlannerAgent'),
        section(1, 'CodeAgent'),
        running(2, 'SecurityAgent', ''),
      ],
    });
    expect(queuedBehind(after)).toEqual({});
    expect(queuedBehind(undefined)).toEqual({});
  });
});

describe('statut affiché d’un fil', () => {
  it('distingue le succès partiel de l’échec', () => {
    expect(runTone('done', '✅ Workflow terminé (100% succès)')).toBe('done');
    expect(runTone('error', '✅ Workflow terminé (50% succès)')).toBe('partial');
    expect(runTone('error', '✅ Workflow terminé (0% succès)')).toBe('error');
    expect(runTone('error', '❌ Erreur lors de l’exécution')).toBe('error');
    expect(runTone('interrupted', '⛔ Génération interrompue')).toBe('interrupted');
  });
});
