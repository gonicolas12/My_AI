/*
 * Tâches planifiées : textes de la liste (dates de Tk « 15/10 08:00 »,
 * dernier résultat) et formulaire du dialogue (scheduler_ui.py de Tk), sans
 * React, pour les tests.
 */

import type { ScheduledStatus, ScheduledTask, TaskFields } from '../../../lib/api';

/** Jours de la semaine, 0 = lundi (core/scheduler.py) */
export const DAY_LABELS = ['Lun', 'Mar', 'Mer', 'Jeu', 'Ven', 'Sam', 'Dim'];

/** Dernier résultat : libellé et couleur (couleurs de Tk ; « différée » en bleu) */
export const STATUS_TEXT: Record<ScheduledStatus, { label: string; color: string }> = {
  success: { label: 'réussie', color: 'var(--success)' },
  partial: { label: 'partielle', color: 'var(--warning)' },
  interrupted: { label: 'interrompue', color: 'var(--warning)' },
  deferred: { label: 'différée (agent occupé)', color: 'var(--info)' },
  error: { label: 'en erreur', color: 'var(--error)' },
};

/** Date ISO → « 15/10 08:00 » (_fmt_dt de Tk), « — » sinon */
export function shortDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '—';
  const pad = (value: number) => String(value).padStart(2, '0');
  return `${pad(date.getDate())}/${pad(date.getMonth() + 1)} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

export type SourceKind = 'single' | 'workflow' | 'debate';
export type ScheduleKind = TaskFields['schedule']['type'];

/** Champs du dialogue, tels que saisis */
export interface TaskForm {
  name: string;
  task: string;
  source: SourceKind;
  agent: string;
  agentA: string;
  agentB: string;
  rounds: string;
  scheduleType: ScheduleKind;
  at: string;
  days: number[];
  every: string;
  unit: 'minutes' | 'heures';
  expr: string;
  runIfMissed: boolean;
}

/** Formulaire d'une nouvelle tâche, ou d'une tâche à modifier (planning repris, comme Tk) */
export function formOf(task: ScheduledTask | null, agentKeys: string[]): TaskForm {
  const schedule = task?.schedule;
  const form: TaskForm = {
    name: task?.name ?? '',
    task: task?.task ?? '',
    source: 'single',
    agent: agentKeys[0] ?? '',
    agentA: agentKeys[0] ?? '',
    agentB: agentKeys[1] ?? agentKeys[0] ?? '',
    rounds: '3',
    scheduleType: schedule?.type ?? 'daily',
    at: '08:00',
    days: [],
    every: '1',
    unit: 'heures',
    expr: '0 8 * * *',
    runIfMissed: task?.run_if_missed ?? true,
  };
  if (!schedule) return form;
  if (schedule.type === 'daily') form.at = schedule.at;
  if (schedule.type === 'weekly') {
    form.at = schedule.at;
    form.days = [...schedule.days];
  }
  if (schedule.type === 'interval') {
    const hours = schedule.seconds % 3600 === 0;
    form.unit = hours ? 'heures' : 'minutes';
    form.every = String(
      hours ? schedule.seconds / 3600 : Math.max(1, Math.round(schedule.seconds / 60)),
    );
  }
  if (schedule.type === 'cron') form.expr = schedule.expr;
  return form;
}

/** Champs envoyés au serveur ; la source compte à la création seulement */
export function fieldsOf(
  form: TaskForm,
  canvas: {
    nodes: NonNullable<TaskFields['source']>['nodes'];
    connections: NonNullable<TaskFields['source']>['connections'];
  },
  creating: boolean,
): TaskFields {
  const fields: TaskFields = {
    name: form.name,
    task: form.task,
    schedule: {
      type: form.scheduleType,
      at: form.at,
      days: form.days,
      every: form.every,
      unit: form.unit,
      expr: form.expr,
    },
    run_if_missed: form.runIfMissed,
  };
  if (!creating) return fields;
  if (form.source === 'debate') {
    const parsed = Number.parseInt(form.rounds, 10);
    fields.source = {
      kind: 'debate',
      agent_a: form.agentA,
      agent_b: form.agentB,
      rounds: Math.max(1, Math.min(10, Number.isNaN(parsed) ? 3 : parsed)),
    };
  } else if (form.source === 'workflow') {
    fields.source = { kind: 'workflow', nodes: canvas.nodes, connections: canvas.connections };
  } else {
    fields.source = { kind: 'single', agent: form.agent };
  }
  return fields;
}
