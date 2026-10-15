import { describe, expect, it } from 'vitest';

import type { ScheduledTask } from '../../../lib/api';
import { fieldsOf, formOf, shortDate } from './scheduleForm';

function task(overrides: Partial<ScheduledTask> = {}): ScheduledTask {
  return {
    id: 'sched_1',
    name: 'Veille',
    enabled: true,
    kind: 'workflow',
    task: 'Résume l’actualité',
    nodes: [{ id: 'n1', agent_type: 'web', name: 'WebAgent', color: '#10b981', icon: '🔍' }],
    connections: [],
    debate: null,
    schedule: { type: 'daily', at: '07:30' },
    run_if_missed: false,
    created_at: '2026-10-14T10:00:00',
    next_run: '2026-10-16T07:30:00',
    last_run: null,
    last_status: null,
    last_output_file: null,
    description: 'tous les jours à 07:30',
    source: 'Agent : WebAgent',
    ...overrides,
  };
}

const CANVAS = {
  nodes: [{ id: '0', agent_type: 'code', name: 'CodeAgent', color: '#3b82f6', icon: '🐍' }],
  connections: [],
};

describe('formulaire d’une tâche planifiée', () => {
  it('écrit les dates comme Tk', () => {
    expect(shortDate('2026-10-05T08:03:00')).toBe('05/10 08:03');
    expect(shortDate(null)).toBe('—');
    expect(shortDate('pas une date')).toBe('—');
  });

  it('part des valeurs de Tk pour une nouvelle tâche', () => {
    const form = formOf(null, ['code', 'web']);
    expect(form).toMatchObject({
      source: 'single',
      agent: 'code',
      agentA: 'code',
      agentB: 'web',
      rounds: '3',
      scheduleType: 'daily',
      at: '08:00',
      expr: '0 8 * * *',
      runIfMissed: true,
    });
  });

  it('reprend le planning de la tâche à modifier', () => {
    expect(formOf(task(), []).at).toBe('07:30');
    const weekly = formOf(task({ schedule: { type: 'weekly', days: [0, 3], at: '09:00' } }), []);
    expect([weekly.scheduleType, weekly.days, weekly.at]).toEqual(['weekly', [0, 3], '09:00']);
    const hours = formOf(task({ schedule: { type: 'interval', seconds: 7200 } }), []);
    expect([hours.every, hours.unit]).toEqual(['2', 'heures']);
    const minutes = formOf(task({ schedule: { type: 'interval', seconds: 900 } }), []);
    expect([minutes.every, minutes.unit]).toEqual(['15', 'minutes']);
    expect(formOf(task({ schedule: { type: 'cron', expr: '0 18 * * 5' } }), []).expr).toBe(
      '0 18 * * 5',
    );
    expect(formOf(task(), []).runIfMissed).toBe(false);
  });

  it('envoie la source à la création seulement', () => {
    const form = { ...formOf(null, ['code', 'web']), name: 'Audit', task: 'Audite' };
    expect(fieldsOf(form, CANVAS, true).source).toEqual({ kind: 'single', agent: 'code' });
    expect(fieldsOf({ ...form, source: 'workflow' }, CANVAS, true).source).toEqual({
      kind: 'workflow',
      ...CANVAS,
    });
    expect(fieldsOf({ ...form, source: 'debate', rounds: '25' }, CANVAS, true).source).toEqual({
      kind: 'debate',
      agent_a: 'code',
      agent_b: 'web',
      rounds: 10,
    });
    expect(fieldsOf(form, CANVAS, false).source).toBeUndefined();
  });
});
