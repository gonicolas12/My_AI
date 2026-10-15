import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TooltipProvider } from '../../../components/ui/Tooltip';
import type { ScheduledTask } from '../../../lib/api';
import { resetAgents, useAgents } from '../../../stores/agents';
import { resetSchedule, useSchedule } from '../../../stores/schedule';
import { ScheduleSection } from './ScheduleSection';

const api = vi.hoisted(() => ({
  schedule: vi.fn(),
  createScheduledTask: vi.fn(),
  updateScheduledTask: vi.fn(),
  deleteScheduledTask: vi.fn(),
  enableScheduledTask: vi.fn(),
  runScheduledTask: vi.fn(),
  setScheduleBackground: vi.fn(),
  agentRun: vi.fn(),
}));
vi.mock('../../../lib/api', () => ({ api }));

function task(overrides: Partial<ScheduledTask> = {}): ScheduledTask {
  return {
    id: 'sched_1',
    name: 'Veille IA du matin',
    enabled: true,
    kind: 'workflow',
    task: 'Résume l’actualité IA',
    nodes: [{ id: 'n1', agent_type: 'web', name: 'WebAgent', color: '#10b981', icon: '🔍' }],
    connections: [],
    debate: null,
    schedule: { type: 'daily', at: '08:00' },
    run_if_missed: true,
    created_at: '2026-10-14T10:00:00',
    next_run: '2026-10-16T08:00:00',
    last_run: '2026-10-15T08:00:00',
    last_status: 'success',
    last_output_file: 'C:/out/sched_1.md',
    description: 'tous les jours à 08:00',
    source: 'Agent : WebAgent',
    ...overrides,
  };
}

const LIST = {
  croniter: true,
  background: { available: true, registered: false },
};

function wrap() {
  return render(
    <TooltipProvider>
      <ScheduleSection onOpenThread={vi.fn()} />
    </TooltipProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  resetAgents();
  resetSchedule();
  useAgents.setState({
    builtin: [
      { key: 'web', icon: '🔍', name: 'WebAgent', desc: 'Recherche', color: '#10b981' },
      { key: 'code', icon: '🐍', name: 'CodeAgent', desc: 'Code', color: '#3b82f6' },
    ],
    loaded: true,
  });
  const tasks = [
    task(),
    task({
      id: 'sched_2',
      name: 'Débat du soir',
      enabled: false,
      last_run: null,
      last_status: null,
      last_output_file: null,
      description: 'toutes les 2 h',
      source: 'Débat : CodeAgent vs WebAgent',
    }),
  ];
  useSchedule.setState({ ...LIST, tasks, loaded: true });
  api.schedule.mockResolvedValue({ ...LIST, tasks });
});

describe('tâches planifiées', () => {
  it('montre le planning, la prochaine exécution et le dernier résultat', () => {
    useAgents.setState({
      runs: [
        {
          id: 'schedexec_1',
          kind: 'agent',
          origin: 'scheduled',
          title: 'Veille IA du matin',
          task: 'Résume',
          status: 'done',
          status_text: '',
          started_at: '2026-10-15T08:00:00',
          finished_at: '2026-10-15T08:00:30',
          duration_ms: 30000,
          agent_type: 'web',
          color: '#10b981',
          agents: 1,
          schedule_task_id: 'sched_1',
        },
      ],
    });
    wrap();
    const [first, second] = screen.getAllByRole('listitem');
    expect(first).toHaveTextContent('tous les jours à 08:00');
    expect(first).toHaveTextContent('Agent : WebAgent');
    expect(first).toHaveTextContent('prochaine : 16/10 08:00');
    expect(first).toHaveTextContent('dernière : 15/10 08:00 · réussie');
    expect(within(first!).getByRole('button', { name: 'Voir le fil' })).toBeInTheDocument();
    expect(within(first!).getByRole('button', { name: 'Rapport' })).toBeInTheDocument();
    expect(second).toHaveTextContent('prochaine : désactivée');
    expect(within(second!).queryByRole('button', { name: 'Rapport' })).toBeNull();
  });

  it('active, exécute et supprime après confirmation', async () => {
    api.enableScheduledTask.mockResolvedValue({ task: task({ enabled: false }) });
    api.runScheduledTask.mockResolvedValue({ ok: true });
    api.deleteScheduledTask.mockResolvedValue({ ok: true });
    wrap();
    const first = screen.getAllByRole('listitem')[0]!;
    await userEvent.click(
      within(first).getByRole('switch', { name: 'Désactiver Veille IA du matin' }),
    );
    expect(api.enableScheduledTask).toHaveBeenCalledWith('sched_1', false);
    await userEvent.click(within(first).getByRole('button', { name: 'Exécuter maintenant' }));
    expect(api.runScheduledTask).toHaveBeenCalledWith('sched_1');
    await userEvent.click(within(first).getByRole('button', { name: 'Supprimer' }));
    const dialog = await screen.findByRole('dialog', { name: 'Supprimer la tâche' });
    expect(dialog).toHaveTextContent('Supprimer la tâche planifiée « Veille IA du matin » ?');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Supprimer' }));
    await waitFor(() => expect(api.deleteScheduledTask).toHaveBeenCalledWith('sched_1'));
    expect(api.schedule).toHaveBeenCalled(); // liste relue
  });

  it('crée une tâche, et montre le refus du serveur dans le dialogue', async () => {
    api.createScheduledTask
      .mockRejectedValueOnce(new Error('❌ Nom requis.'))
      .mockResolvedValueOnce({ task: task({ id: 'sched_3' }) });
    wrap();
    await userEvent.click(screen.getByRole('button', { name: 'Nouvelle tâche' }));
    const dialog = await screen.findByRole('dialog', { name: 'Nouvelle tâche planifiée' });
    await userEvent.click(within(dialog).getByRole('button', { name: 'Enregistrer' }));
    expect(await within(dialog).findByText('❌ Nom requis.')).toBeInTheDocument();
    await userEvent.type(within(dialog).getByLabelText('Nom'), 'Audit du lundi');
    await userEvent.type(within(dialog).getByLabelText('Tâche / Sujet (débat)'), 'Audite le dépôt');
    await userEvent.click(within(dialog).getByRole('radio', { name: 'Hebdo' }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Lun' }));
    await userEvent.click(within(dialog).getByRole('button', { name: 'Enregistrer' }));
    await waitFor(() => expect(screen.queryByRole('dialog')).toBeNull());
    expect(api.createScheduledTask).toHaveBeenLastCalledWith({
      name: 'Audit du lundi',
      task: 'Audite le dépôt',
      schedule: {
        type: 'weekly',
        at: '08:00',
        days: [0],
        every: '1',
        unit: 'heures',
        expr: '0 8 * * *',
      },
      run_if_missed: true,
      source: { kind: 'single', agent: 'web' },
    });
  });

  it('modifie une tâche sans toucher à sa source', async () => {
    api.updateScheduledTask.mockResolvedValue({ task: task() });
    wrap();
    const first = screen.getAllByRole('listitem')[0]!;
    await userEvent.click(within(first).getByRole('button', { name: 'Modifier' }));
    const dialog = await screen.findByRole('dialog', { name: 'Modifier la tâche' });
    expect(dialog).toHaveTextContent('Agent : WebAgent');
    expect(within(dialog).queryByRole('radiogroup', { name: 'Source' })).toBeNull();
    expect(within(dialog).getByLabelText('Heure')).toHaveValue('08:00');
    await userEvent.click(within(dialog).getByRole('button', { name: 'Enregistrer' }));
    await waitFor(() => expect(api.updateScheduledTask).toHaveBeenCalled());
    expect(api.updateScheduledTask).toHaveBeenCalledWith(
      'sched_1',
      expect.not.objectContaining({ source: expect.anything() as unknown }),
    );
  });

  it('exécution appli fermée : l’interrupteur enregistre la tâche de Windows', async () => {
    api.setScheduleBackground.mockResolvedValue({ registered: true, ok: true, message: 'ok' });
    wrap();
    await userEvent.click(screen.getByRole('switch', { name: "Exécuter même l'appli fermée" }));
    expect(api.setScheduleBackground).toHaveBeenCalledWith(true);
  });
});
