/*
 * Créer ou modifier une tâche planifiée (_open_scheduler_dialog de Tk) : nom,
 * source (agent seul, workflow du canvas courant, débat ; figée à la
 * modification), tâche ou sujet, planning (quotidien, hebdo, intervalle,
 * cron) et rattrapage. Les règles et messages sont ceux de Tk, vérifiés par le
 * serveur (interfaces/desktop/schedule.py) et affichés sous les champs.
 */

import { TriangleAlert } from 'lucide-react';
import { type ReactNode, useId, useState } from 'react';

import { Button } from '../../../components/ui/Button';
import { Dialog } from '../../../components/ui/Dialog';
import type { ScheduledTask } from '../../../lib/api';
import { cn } from '../../../lib/cn';
import { errorText, useAgents } from '../../../stores/agents';
import { saveScheduledTask, useSchedule } from '../../../stores/schedule';
import { useWorkflow } from '../canvas/workflowStore';
import {
  DAY_LABELS,
  fieldsOf,
  formOf,
  type ScheduleKind,
  type SourceKind,
  type TaskForm,
} from './scheduleForm';

const fieldClass =
  'h-9 rounded-md border border-line bg-bg px-2.5 text-sm text-fg outline-none placeholder:text-fg-3 focus:border-line-2 disabled:text-fg-3';

const SOURCES: [SourceKind, string][] = [
  ['single', 'Agent seul'],
  ['workflow', 'Workflow (canvas)'],
  ['debate', 'Débat'],
];

const SCHEDULES: [ScheduleKind, string][] = [
  ['daily', 'Quotidien'],
  ['weekly', 'Hebdo'],
  ['interval', 'Intervalle'],
  ['cron', 'Cron'],
];

function Label({ htmlFor, children }: { htmlFor?: string; children: ReactNode }) {
  return (
    <label htmlFor={htmlFor} className="text-sm font-semibold text-fg">
      {children}
    </label>
  );
}

/** Choix exclusif en boutons (boutons radio de Tk) */
function Choices<T extends string>({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: T;
  options: [T, string][];
  onChange: (value: T) => void;
}) {
  return (
    <div role="radiogroup" aria-label={label} className="flex flex-wrap gap-1.5">
      {options.map(([key, text]) => (
        <button
          key={key}
          type="button"
          role="radio"
          aria-checked={value === key}
          onClick={() => onChange(key)}
          className={cn(
            'h-8 rounded-md border px-3 text-sm transition-colors duration-150',
            value === key
              ? 'border-accent bg-accent-soft text-fg'
              : 'border-line text-fg-2 hover:bg-hover hover:text-fg',
          )}
        >
          {text}
        </button>
      ))}
    </div>
  );
}

/** Workflow du canvas courant, figé dans la tâche (identifiants en texte, comme Tk) */
function canvasSource() {
  const { nodes, edges } = useWorkflow.getState();
  return {
    nodes: nodes.map((node) => ({
      id: String(node.id),
      agent_type: node.data.agentType,
      name: node.data.name,
      color: node.data.color,
      icon: node.data.icon,
    })),
    connections: edges.map((edge) => ({ from: String(edge.source), to: String(edge.target) })),
  };
}

interface ScheduleDialogProps {
  /** Tâche à modifier ; null : création */
  task: ScheduledTask | null;
  onClose: () => void;
}

/** Monté le temps de la saisie : ses champs partent de la tâche à modifier */
export function ScheduleDialog({ task, onClose }: ScheduleDialogProps) {
  const builtin = useAgents((state) => state.builtin);
  const custom = useAgents((state) => state.custom);
  const agents = [...builtin, ...custom];
  const croniter = useSchedule((state) => state.croniter);
  const canvasNodes = useWorkflow((state) => state.nodes.length);
  const [form, setForm] = useState<TaskForm>(() =>
    formOf(
      task,
      agents.map((agent) => agent.key),
    ),
  );
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const ids = {
    name: useId(),
    agent: useId(),
    agentA: useId(),
    agentB: useId(),
    rounds: useId(),
    task: useId(),
    at: useId(),
    every: useId(),
    unit: useId(),
    expr: useId(),
    missed: useId(),
  };
  const creating = task === null;
  const set = (patch: Partial<TaskForm>) => setForm((current) => ({ ...current, ...patch }));

  const submit = async () => {
    setBusy(true);
    setError('');
    try {
      await saveScheduledTask(task?.id ?? null, fieldsOf(form, canvasSource(), creating));
      onClose();
    } catch (failure) {
      setError(errorText(failure));
      setBusy(false);
    }
  };

  const options = agents.map((agent) => (
    <option key={agent.key} value={agent.key}>
      {agent.name}
    </option>
  ));

  return (
    <Dialog
      open
      onOpenChange={(next) => {
        if (!next && !busy) onClose();
      }}
      title={creating ? 'Nouvelle tâche planifiée' : 'Modifier la tâche'}
      width={560}
      dismissible={!busy}
      footer={
        <>
          <Button variant="secondary" disabled={busy} onClick={onClose}>
            Annuler
          </Button>
          <Button variant="primary" disabled={busy} onClick={() => void submit()}>
            Enregistrer
          </Button>
        </>
      }
    >
      <form
        className="flex max-h-[min(70vh,640px)] flex-col gap-3 overflow-y-auto pr-1"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <Label htmlFor={ids.name}>Nom</Label>
        <input
          id={ids.name}
          value={form.name}
          disabled={busy}
          autoFocus
          maxLength={200}
          placeholder="Ex : Veille IA matinale"
          onChange={(event) => set({ name: event.target.value })}
          className={fieldClass}
        />

        <Label>Source</Label>
        {creating ? (
          <>
            <Choices
              label="Source"
              value={form.source}
              options={SOURCES}
              onChange={(source) => set({ source })}
            />
            {form.source === 'single' ? (
              <select
                id={ids.agent}
                aria-label="Agent"
                value={form.agent}
                disabled={busy}
                onChange={(event) => set({ agent: event.target.value })}
                className={fieldClass}
              >
                {options}
              </select>
            ) : null}
            {form.source === 'workflow' ? (
              canvasNodes ? (
                <p className="text-sm text-fg-2">
                  Utilise le workflow du canvas ({canvasNodes} nœud{canvasNodes > 1 ? 's' : ''}).
                </p>
              ) : (
                <p className="flex items-center gap-2 text-sm text-warning">
                  <TriangleAlert size={14} />
                  Le canvas est vide : déposez des agents d’abord.
                </p>
              )
            ) : null}
            {form.source === 'debate' ? (
              <div className="grid grid-cols-[auto_1fr] items-center gap-x-3 gap-y-2">
                <label htmlFor={ids.agentA} className="text-sm text-fg-2">
                  Proposant
                </label>
                <select
                  id={ids.agentA}
                  value={form.agentA}
                  disabled={busy}
                  onChange={(event) => set({ agentA: event.target.value })}
                  className={fieldClass}
                >
                  {options}
                </select>
                <label htmlFor={ids.agentB} className="text-sm text-fg-2">
                  Opposant
                </label>
                <select
                  id={ids.agentB}
                  value={form.agentB}
                  disabled={busy}
                  onChange={(event) => set({ agentB: event.target.value })}
                  className={fieldClass}
                >
                  {options}
                </select>
                <label htmlFor={ids.rounds} className="text-sm text-fg-2">
                  Tours
                </label>
                <input
                  id={ids.rounds}
                  type="number"
                  min={1}
                  max={10}
                  value={form.rounds}
                  disabled={busy}
                  onChange={(event) => set({ rounds: event.target.value })}
                  className={cn(fieldClass, 'w-20 tabular-nums')}
                />
              </div>
            ) : null}
          </>
        ) : (
          <p className="text-sm text-fg-2">
            {task.source}
            <span className="block text-xs text-fg-3">
              La source ne change pas : pour en changer, supprimez la tâche et recréez-la.
            </span>
          </p>
        )}

        <Label htmlFor={ids.task}>Tâche / Sujet (débat)</Label>
        <textarea
          id={ids.task}
          value={form.task}
          disabled={busy}
          rows={3}
          maxLength={100_000}
          onChange={(event) => set({ task: event.target.value })}
          className="resize-none rounded-md border border-line bg-bg px-3 py-2 text-sm leading-relaxed text-fg outline-none focus:border-line-2"
        />

        <Label>Planning</Label>
        <Choices
          label="Planning"
          value={form.scheduleType}
          options={SCHEDULES}
          onChange={(scheduleType) => set({ scheduleType })}
        />
        {form.scheduleType === 'daily' || form.scheduleType === 'weekly' ? (
          <div className="flex flex-col gap-2">
            <div className="flex items-center gap-3">
              <label htmlFor={ids.at} className="text-sm text-fg-2">
                Heure
              </label>
              <input
                id={ids.at}
                type="time"
                value={form.at}
                disabled={busy}
                onChange={(event) => set({ at: event.target.value })}
                className={cn(fieldClass, 'w-28 tabular-nums')}
              />
            </div>
            {form.scheduleType === 'weekly' ? (
              <div role="group" aria-label="Jours" className="flex flex-wrap gap-1.5">
                {DAY_LABELS.map((day, index) => {
                  const checked = form.days.includes(index);
                  return (
                    <button
                      key={day}
                      type="button"
                      aria-pressed={checked}
                      onClick={() =>
                        set({
                          days: checked
                            ? form.days.filter((item) => item !== index)
                            : [...form.days, index].sort((a, b) => a - b),
                        })
                      }
                      className={cn(
                        'h-8 w-12 rounded-md border text-sm transition-colors duration-150',
                        checked
                          ? 'border-accent bg-accent-soft text-fg'
                          : 'border-line text-fg-2 hover:bg-hover hover:text-fg',
                      )}
                    >
                      {day}
                    </button>
                  );
                })}
              </div>
            ) : null}
          </div>
        ) : null}
        {form.scheduleType === 'interval' ? (
          <div className="flex items-center gap-3">
            <label htmlFor={ids.every} className="text-sm text-fg-2">
              Toutes les
            </label>
            <input
              id={ids.every}
              type="number"
              min={1}
              value={form.every}
              disabled={busy}
              onChange={(event) => set({ every: event.target.value })}
              className={cn(fieldClass, 'w-20 tabular-nums')}
            />
            <select
              id={ids.unit}
              aria-label="Unité"
              value={form.unit}
              disabled={busy}
              onChange={(event) => set({ unit: event.target.value as TaskForm['unit'] })}
              className={cn(fieldClass, 'w-28')}
            >
              <option value="minutes">minutes</option>
              <option value="heures">heures</option>
            </select>
          </div>
        ) : null}
        {form.scheduleType === 'cron' ? (
          <div className="flex flex-col gap-2">
            {!croniter ? (
              <p className="flex items-center gap-2 text-sm text-warning">
                <TriangleAlert size={14} />
                croniter requis (pip install croniter) pour les expressions cron.
              </p>
            ) : null}
            <input
              id={ids.expr}
              aria-label="Expression cron"
              value={form.expr}
              disabled={busy}
              spellCheck={false}
              placeholder="min heure jour mois jour_semaine"
              onChange={(event) => set({ expr: event.target.value })}
              className={cn(fieldClass, 'font-mono')}
            />
          </div>
        ) : null}

        <label htmlFor={ids.missed} className="mt-1 flex items-center gap-2 text-sm text-fg">
          <input
            id={ids.missed}
            type="checkbox"
            checked={form.runIfMissed}
            disabled={busy}
            onChange={(event) => set({ runIfMissed: event.target.checked })}
            className="h-4 w-4 accent-[var(--accent)]"
          />
          Rattraper au prochain démarrage si manquée
        </label>
        <div className="min-h-5 text-sm text-error" aria-live="polite">
          {error}
        </div>
      </form>
    </Dialog>
  );
}
