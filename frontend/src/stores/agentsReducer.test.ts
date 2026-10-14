import { describe, expect, it } from 'vitest';

import type { AnyAgentEvent, RunView } from '../lib/events';
import { applyAgentEvent, EMPTY_RUNS, type RunsState, withLoadedRun } from './agentsReducer';

function run(overrides: Partial<RunView> = {}): RunView {
  return {
    id: 'exec_1',
    kind: 'workflow',
    title: 'Workflow · 2 agents',
    task: 'Une API\nREST',
    attachments: [],
    sources: [],
    nodes: [
      { id: 0, agent_type: 'code', name: 'CodeAgent', color: '#3b82f6' },
      { id: 1, agent_type: 'debug', name: 'DebugAgent', color: '#ef4444' },
    ],
    connections: [{ from: 0, to: 1 }],
    plan: { mode: 'sequential', steps: [[0], [1]], isolated: [] },
    mode: null,
    status: 'running',
    status_text: '',
    error: null,
    started_at: new Date(Date.now() - 2000).toISOString(),
    finished_at: null,
    duration_ms: null,
    sections: [],
    node_status: { '0': 'idle', '1': 'idle' },
    ...overrides,
  };
}

let seq = 0;
function event<T extends AnyAgentEvent['type']>(
  type: T,
  payload: Extract<AnyAgentEvent, { type: T }>['payload'],
  at?: number,
): AnyAgentEvent {
  seq = at ?? seq + 1;
  return { type, payload, seq, conversation_id: null, message_id: null } as AnyAgentEvent;
}

function apply(state: RunsState, ...events: AnyAgentEvent[]): RunsState {
  return events.reduce(applyAgentEvent, state);
}

describe('fils d’exécution', () => {
  it('un nouveau fil s’ouvre, en tête de liste, et occupe l’exécuteur', () => {
    const state = apply(EMPTY_RUNS, event('agents.run_created', { run: run() }));
    expect(state.openRunId).toBe('exec_1');
    expect(state.active).toBe('exec_1');
    expect(state.busy).toBe(true);
    expect(state.runs[0]).toMatchObject({ id: 'exec_1', task: 'Une API REST', agents: 2 });
  });

  it('recompose le texte d’une section à partir de ses suites', () => {
    const state = apply(
      EMPTY_RUNS,
      event('agents.run_created', { run: run() }),
      event('agents.agent_exec_start', { exec_id: 'exec_1', mode: 'sequential' }),
      event('agents.agent_section_start', {
        exec_id: 'exec_1',
        section_id: 0,
        title: 'CodeAgent',
        color: '#3b82f6',
      }),
      event('agents.agent_section_delta', {
        exec_id: 'exec_1',
        section_id: 0,
        text: 'Bon',
        offset: 0,
      }),
      event('agents.agent_section_delta', {
        exec_id: 'exec_1',
        section_id: 0,
        text: 'jour',
        offset: 3,
      }),
      // Doublon (rejoué après une reconnexion) : ignoré
      event('agents.agent_section_delta', {
        exec_id: 'exec_1',
        section_id: 0,
        text: 'jour',
        offset: 3,
      }),
      event('agents.agent_node_status', { exec_id: 'exec_1', node_id: 0, status: 'running' }),
    );
    const detail = state.details.exec_1!;
    expect(detail.mode).toBe('sequential');
    expect(detail.sections).toHaveLength(1);
    expect(detail.sections[0]).toMatchObject({
      text: 'Bonjour',
      agent_type: 'code',
      status: 'running',
    });
    expect(detail.node_status['0']).toBe('running');
    expect(state.stale).toEqual([]);
  });

  it('une suite qui laisse un trou fait relire le fil', () => {
    const state = apply(
      EMPTY_RUNS,
      event('agents.run_created', { run: run() }),
      event('agents.agent_section_delta', {
        exec_id: 'exec_1',
        section_id: 0,
        text: 'fin',
        offset: 12,
      }),
    );
    expect(state.stale).toEqual(['exec_1']);
    expect(state.details.exec_1!.sections).toEqual([]);
    const reloaded = withLoadedRun(state, run({ sections: [] }), seq + 10);
    expect(reloaded.stale).toEqual([]);
    expect(reloaded.floors.exec_1).toBe(seq + 10);
  });

  it('un texte entier remplace la section', () => {
    const state = apply(
      EMPTY_RUNS,
      event('agents.run_created', { run: run() }),
      event('agents.agent_section_delta', {
        exec_id: 'exec_1',
        section_id: 1,
        text: 'brouillon',
        offset: 0,
      }),
      event('agents.agent_section_text', {
        exec_id: 'exec_1',
        section_id: 1,
        text: 'Réponse finale',
      }),
      event('agents.agent_section_end', { exec_id: 'exec_1', section_id: 1, success: true }),
    );
    const section = state.details.exec_1!.sections[0]!;
    expect(section).toMatchObject({
      id: 1,
      title: 'DebugAgent',
      text: 'Réponse finale',
      status: 'done',
    });
    expect(section.finished_at).not.toBeNull();
  });

  it('la fin du fil le clôt, libère l’exécuteur et met la liste à jour', () => {
    const state = apply(
      EMPTY_RUNS,
      event('agents.run_created', { run: run() }),
      event('agents.agent_section_start', {
        exec_id: 'exec_1',
        section_id: 0,
        title: 'CodeAgent',
        color: '',
      }),
      event('agents.agent_node_status', { exec_id: 'exec_1', node_id: 0, status: 'running' }),
      event('agents.agent_exec_end', {
        exec_id: 'exec_1',
        success: false,
        interrupted: true,
        status_text: '⛔ Génération interrompue',
      }),
    );
    const detail = state.details.exec_1!;
    expect(detail.status).toBe('interrupted');
    expect(detail.duration_ms).toBeGreaterThanOrEqual(1500);
    // Ce qui tournait encore passe en erreur, comme Run.finish côté serveur
    expect(detail.sections[0]!.status).toBe('error');
    expect(detail.node_status['0']).toBe('error');
    expect(state.active).toBeNull();
    expect(state.busy).toBe(false);
    expect(state.runs[0]).toMatchObject({
      status: 'interrupted',
      status_text: '⛔ Génération interrompue',
    });
  });

  it('une exécution refusée finit en erreur avec son message', () => {
    const state = apply(
      EMPTY_RUNS,
      event('agents.run_created', { run: run() }),
      event('agents.agent_exec_error', {
        exec_id: 'exec_1',
        message: 'Une exécution est déjà en cours.',
      }),
    );
    expect(state.details.exec_1).toMatchObject({
      status: 'error',
      status_text: '❌ Une exécution est déjà en cours.',
      error: 'Une exécution est déjà en cours.',
    });
  });

  it('ignore les événements plus anciens que la lecture du fil, et les fils inconnus', () => {
    const loaded = withLoadedRun(
      { ...EMPTY_RUNS, runs: [] },
      run({
        sections: [
          {
            id: 0,
            title: 'CodeAgent',
            color: '',
            agent_type: 'code',
            text: 'Bonjour',
            status: 'running',
            started_at: null,
            finished_at: null,
          },
        ],
      }),
      100,
    );
    const old = event(
      'agents.agent_section_delta',
      { exec_id: 'exec_1', section_id: 0, text: 'x', offset: 7 },
      90,
    );
    expect(applyAgentEvent(loaded, old)).toBe(loaded);
    const unknown = event('agents.agent_exec_start', { exec_id: 'exec_9', mode: 'single' }, 101);
    expect(applyAgentEvent(loaded, unknown)).toBe(loaded);
    const fresh = event(
      'agents.agent_section_delta',
      { exec_id: 'exec_1', section_id: 0, text: ' !', offset: 7 },
      101,
    );
    expect(applyAgentEvent(loaded, fresh).details.exec_1!.sections[0]!.text).toBe('Bonjour !');
  });
});
