/*
 * Vue des tâches planifiées (§8 : « prochaine exécution, dernier résultat ») :
 * la section « 📅 Tâches planifiées » de Tk (scheduler_ui.py). Chaque tâche
 * montre son planning, sa source, sa prochaine exécution et son dernier
 * résultat, avec son fil (D37) et son rapport ; actions : activer,
 * exécuter maintenant, modifier, supprimer. Sous Windows, « Exécuter même
 * l'appli fermée » enregistre la tâche du Planificateur de tâches.
 */

import {
  CalendarClock,
  CalendarPlus,
  CirclePause,
  FileText,
  ListTree,
  Pencil,
  Play,
  Trash2,
} from 'lucide-react';
import { useState } from 'react';

import { Button, IconButton } from '../../../components/ui/Button';
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog';
import { Switch } from '../../../components/ui/Switch';
import { useT } from '../../../i18n';
import { openFile } from '../../../lib/actions';
import type { ScheduledTask } from '../../../lib/api';
import { cn } from '../../../lib/cn';
import { openRun, useAgents } from '../../../stores/agents';
import {
  deleteScheduledTask,
  runScheduledTask,
  setScheduleBackground,
  setTaskEnabled,
  useSchedule,
} from '../../../stores/schedule';
import { ScheduleDialog } from './ScheduleDialog';
import { shortDate, STATUS_TEXT } from './scheduleForm';

function LastResult({
  task,
  onOpenThread,
}: {
  task: ScheduledTask;
  onOpenThread: (id: string) => void;
}) {
  const t = useT();
  // Fil de la dernière exécution (les plus récents d'abord)
  const runId = useAgents(
    (state) => state.runs.find((run) => run.schedule_task_id === task.id)?.id ?? null,
  );
  if (!task.last_run && task.last_status !== 'deferred') return null;
  const status = task.last_status ? STATUS_TEXT[task.last_status] : null;
  return (
    <span className="flex flex-wrap items-center gap-x-2 gap-y-0.5">
      <span>
        {t('schedule.last', { date: shortDate(task.last_run) })}
        {status ? <span style={{ color: status.color }}> · {t(status.label)}</span> : null}
      </span>
      {runId ? (
        <button
          type="button"
          onClick={() => onOpenThread(runId)}
          className="inline-flex items-center gap-1 text-link hover:underline"
        >
          <ListTree size={12} />
          {t('schedule.viewThread')}
        </button>
      ) : null}
      {task.last_output_file ? (
        <button
          type="button"
          onClick={() => void openFile(task.last_output_file as string)}
          title={task.last_output_file}
          className="inline-flex items-center gap-1 text-link hover:underline"
        >
          <FileText size={12} />
          {t('agents.thread.report')}
        </button>
      ) : null}
    </span>
  );
}

function TaskRow({
  task,
  onEdit,
  onDelete,
  onOpenThread,
}: {
  task: ScheduledTask;
  onEdit: () => void;
  onDelete: () => void;
  onOpenThread: (id: string) => void;
}) {
  const t = useT();
  return (
    <li className="flex items-center gap-3 rounded-lg border border-line/70 bg-bg px-4 py-3">
      {task.enabled ? (
        <CalendarClock size={17} className="shrink-0 text-fg-2" />
      ) : (
        <CirclePause size={17} className="shrink-0 text-fg-3" />
      )}
      <div className="min-w-0 flex-1">
        <div
          className={cn(
            'truncate text-[15px] font-semibold',
            task.enabled ? 'text-fg' : 'text-fg-3',
          )}
        >
          {task.name}
        </div>
        <div className="mt-0.5 flex flex-wrap items-center gap-x-2 gap-y-0.5 text-xs text-fg-2">
          <span>{task.description}</span>
          <span className="text-fg-3">·</span>
          <span>{task.source}</span>
          <span className="text-fg-3">·</span>
          <span>
            {t('schedule.next', {
              date: task.enabled ? shortDate(task.next_run) : t('schedule.disabled'),
            })}
          </span>
        </div>
        <div className="mt-0.5 text-xs text-fg-2">
          <LastResult task={task} onOpenThread={onOpenThread} />
        </div>
      </div>
      <div className="flex shrink-0 items-center gap-1">
        <Switch
          checked={task.enabled}
          onCheckedChange={(enabled) => void setTaskEnabled(task.id, enabled)}
          label={
            task.enabled
              ? t('schedule.disable', { name: task.name })
              : t('schedule.enable', { name: task.name })
          }
        />
        <span className="ms-1.5 flex items-center">
          <IconButton label={t('schedule.runNow')} onClick={() => void runScheduledTask(task.id)}>
            <Play size={15} className="text-success" />
          </IconButton>
          <IconButton label={t('common.edit')} onClick={onEdit}>
            <Pencil size={15} />
          </IconButton>
          <IconButton label={t('common.delete')} onClick={onDelete} className="hover:text-error">
            <Trash2 size={15} />
          </IconButton>
        </span>
      </div>
    </li>
  );
}

export function ScheduleSection({ onOpenThread }: { onOpenThread: (runId: string) => void }) {
  const t = useT();
  const tasks = useSchedule((state) => state.tasks);
  const loaded = useSchedule((state) => state.loaded);
  const background = useSchedule((state) => state.background);
  // undefined : fermé ; null : nouvelle tâche
  const [editing, setEditing] = useState<ScheduledTask | null | undefined>(undefined);
  const [deleting, setDeleting] = useState<ScheduledTask | null>(null);

  const openThread = (runId: string) => {
    openRun(runId);
    onOpenThread(runId);
  };

  return (
    <section aria-labelledby="agents-schedule" className="flex flex-col gap-3">
      <div className="flex items-center gap-3">
        <div className="min-w-0 flex-1">
          <h2 id="agents-schedule" className="text-lg font-semibold text-fg">
            {t('schedule.title')}
          </h2>
          <p className="text-sm text-fg-2">{t('schedule.description')}</p>
        </div>
        <Button variant="secondary" onClick={() => setEditing(null)}>
          <CalendarPlus size={15} className="text-fg-2" />
          {t('schedule.new')}
        </Button>
      </div>
      {background.available ? (
        <label className="flex w-fit items-center gap-2.5 text-sm text-fg">
          <Switch
            checked={background.registered}
            onCheckedChange={(enabled) => void setScheduleBackground(enabled)}
            label={t('schedule.background')}
          />
          {t('schedule.background')}
          <span className="text-fg-3">{t('schedule.backgroundNote')}</span>
        </label>
      ) : null}
      {tasks.length ? (
        <ul className="flex flex-col gap-2" aria-label={t('schedule.title')}>
          {tasks.map((task) => (
            <TaskRow
              key={task.id}
              task={task}
              onEdit={() => setEditing(task)}
              onDelete={() => setDeleting(task)}
              onOpenThread={openThread}
            />
          ))}
        </ul>
      ) : loaded ? (
        <p className="rounded-xl border border-dashed border-line px-5 py-4 text-sm text-fg-2">
          {t('schedule.empty')}
        </p>
      ) : null}
      {editing !== undefined ? (
        <ScheduleDialog task={editing} onClose={() => setEditing(undefined)} />
      ) : null}
      <ConfirmDialog
        open={deleting !== null}
        onOpenChange={(open) => {
          if (!open) setDeleting(null);
        }}
        title={t('schedule.delete.title')}
        message={t('schedule.delete.message', { name: deleting?.name ?? '' })}
        confirmLabel={t('common.delete')}
        danger
        onConfirm={() => {
          if (deleting) void deleteScheduledTask(deleting.id);
        }}
      />
    </section>
  );
}
