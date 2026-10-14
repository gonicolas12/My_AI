import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TooltipProvider } from '../../components/ui/Tooltip';
import type { AgentInfo, RunView } from '../../lib/events';
import { resetAgents, useAgents } from '../../stores/agents';
import { summaryOf } from '../../stores/agentsReducer';
import { AgentDialog } from './AgentDialog';
import { AgentGrid } from './AgentGrid';
import { resetWorkflow, useWorkflow } from './canvas/workflowStore';
import { RunList } from './runs/RunList';
import { ThreadView } from './runs/ThreadView';
import { TaskZone } from './TaskZone';

const api = vi.hoisted(() => ({
  agents: vi.fn(),
  createAgent: vi.fn(),
  editAgent: vi.fn(),
  deleteAgent: vi.fn(),
  agentRun: vi.fn(),
  stopRun: vi.fn(),
  fileLinks: vi.fn(() => Promise.resolve({ links: {} })),
}));
vi.mock('../../lib/api', () => ({ api }));

const BUILTIN: AgentInfo[] = [
  {
    key: 'code',
    icon: '🐍',
    name: 'CodeAgent',
    desc: 'Génération et debug de code',
    color: '#3b82f6',
  },
  { key: 'debug', icon: '🐛', name: 'DebugAgent', desc: 'Debug et correction', color: '#ef4444' },
];
const CUSTOM: AgentInfo = {
  key: 'custom_seo_1',
  icon: '🧩',
  name: 'SEOAgent',
  desc: 'Optimisation SEO',
  full_desc: 'Optimisation SEO des pages',
  color: '#16a34a',
  custom: true,
};

function wrap(ui: React.ReactNode) {
  return render(<TooltipProvider>{ui}</TooltipProvider>);
}

beforeEach(() => {
  vi.clearAllMocks();
  resetAgents();
  resetWorkflow();
  useAgents.setState({ builtin: BUILTIN, custom: [CUSTOM], loaded: true });
  api.agents.mockResolvedValue({ builtin: BUILTIN, custom: [CUSTOM], default_model: 'my_ai' });
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

describe('grille des agents', () => {
  it('ajoute un agent au workflow par un clic ou Entrée, en cascade', async () => {
    wrap(<AgentGrid />);
    await userEvent.click(screen.getByRole('button', { name: /^CodeAgent :/ }));
    screen.getByRole('button', { name: /^DebugAgent :/ }).focus();
    await userEvent.keyboard('{Enter}');
    const nodes = useWorkflow.getState().nodes;
    expect(nodes.map((node) => [node.id, node.data.agentType, node.data.icon])).toEqual([
      ['0', 'code', '🐍'],
      ['1', 'debug', '🐛'],
    ]);
    expect(nodes[1]!.position).toEqual({ x: 375, y: 50 });
  });

  it('supprime un agent personnalisé après confirmation, et ses nœuds du canvas', async () => {
    api.deleteAgent.mockResolvedValue({ ok: true });
    api.agents.mockResolvedValue({ builtin: BUILTIN, custom: [], default_model: 'my_ai' });
    wrap(<AgentGrid />);
    await userEvent.click(screen.getByRole('button', { name: /^SEOAgent :/ }));
    expect(useWorkflow.getState().nodes[0]!.data.icon).toBe('🤖'); // comme Tk
    await userEvent.click(screen.getByRole('button', { name: 'Supprimer SEOAgent' }));
    const dialog = await screen.findByRole('dialog', { name: "Supprimer l'agent" });
    expect(dialog).toHaveTextContent("Voulez-vous vraiment supprimer l'agent 'SEOAgent' ?");
    await userEvent.click(within(dialog).getByRole('button', { name: 'Supprimer' }));
    await waitFor(() => expect(useWorkflow.getState().nodes).toHaveLength(0));
    expect(api.deleteAgent).toHaveBeenCalledWith('custom_seo_1');
  });
});

describe('dialogue d’un agent personnalisé', () => {
  it('reprend les contrôles de Tk, puis crée l’agent', async () => {
    const onClose = vi.fn();
    api.createAgent.mockResolvedValue({ agent: { ...CUSTOM, key: 'custom_x', name: 'X' } });
    wrap(<AgentDialog agent={null} onClose={onClose} />);
    await userEvent.click(screen.getByRole('button', { name: 'Créer' }));
    expect(screen.getByText("Veuillez entrer un nom pour l'agent.")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Nom de l'agent"), '  TraducteurAgent ');
    await userEvent.click(screen.getByRole('button', { name: 'Créer' }));
    expect(screen.getByText("Veuillez décrire le rôle de l'agent.")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Rôle / Description'), 'Traduction');
    await userEvent.click(screen.getByRole('button', { name: 'Créer' }));
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(api.createAgent).toHaveBeenCalledWith('TraducteurAgent', 'Traduction');
  });

  it('montre l’erreur du serveur et garde le dialogue ouvert', async () => {
    const onClose = vi.fn();
    api.editAgent.mockRejectedValue(new Error('❌ Erreur : Ollama n’a pas répondu.'));
    wrap(<AgentDialog agent={CUSTOM} onClose={onClose} />);
    expect(screen.getByLabelText('Rôle / Description')).toHaveValue('Optimisation SEO des pages');
    await userEvent.type(screen.getByLabelText('Rôle / Description'), ' et des articles');
    await userEvent.click(screen.getByRole('button', { name: 'Sauvegarder' }));
    expect(await screen.findByText('❌ Erreur : Ollama n’a pas répondu.')).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });
});

describe('zone de tâche', () => {
  it('Ctrl+Entrée exécute, Débat attend la phase 4b, Vider vide le canvas', async () => {
    const onExecute = vi.fn();
    useWorkflow.setState({
      nodes: [
        {
          id: '0',
          type: 'agent',
          position: { x: 0, y: 0 },
          data: { agentType: 'code', name: 'CodeAgent', color: '#3b82f6', icon: '🐍' },
        },
      ],
      nextId: 1,
    });
    wrap(<TaskZone onExecute={onExecute} />);
    const task = screen.getByRole('textbox', { name: 'Tâche' });
    await userEvent.type(task, 'Écris un tri');
    fireEvent.keyDown(task, { key: 'Enter', ctrlKey: true });
    expect(onExecute).toHaveBeenCalledTimes(1);
    expect(useAgents.getState().task).toBe('Écris un tri');
    expect(screen.getByRole('button', { name: 'Débat' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Vider' }));
    expect(useWorkflow.getState().nodes).toHaveLength(0);
  });

  it('pendant une exécution, Exécuter devient Arrêter', async () => {
    api.stopRun.mockResolvedValue({ stopped: true });
    useAgents.setState({ active: 'exec_1' });
    wrap(<TaskZone onExecute={vi.fn()} />);
    expect(screen.queryByRole('button', { name: 'Exécuter' })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Arrêter' }));
    expect(api.stopRun).toHaveBeenCalledWith('exec_1');
  });
});

function finishedRun(overrides: Partial<RunView> = {}): RunView {
  return {
    id: 'exec_1',
    kind: 'agent',
    title: 'OptimizerAgent',
    task: 'Optimise ce code',
    attachments: [{ path: 'C:/p/utils.py', name: 'utils.py', type: 'Code' }],
    sources: [{ name: 'utils.py', text: 'def f(x):\n    print(x)\n    return x == None\n' }],
    nodes: [{ id: 0, agent_type: 'optimizer', name: 'OptimizerAgent', color: '#14b8a6' }],
    connections: [],
    plan: { mode: 'single', steps: [[0]], isolated: [] },
    mode: 'single',
    status: 'done',
    status_text: '✅ Tâche terminée avec OptimizerAgent',
    error: null,
    started_at: '2026-10-14T14:02:00',
    finished_at: '2026-10-14T14:02:03',
    duration_ms: 3000,
    sections: [
      {
        id: 0,
        title: 'OptimizerAgent',
        color: '#14b8a6',
        agent_type: 'optimizer',
        text: 'Version revue :\n\n```python\ndef f(x):\n    return x is None\n```\n\nPlus de trace.',
        status: 'done',
        started_at: '2026-10-14T14:02:00',
        finished_at: '2026-10-14T14:02:03',
      },
    ],
    node_status: { '0': 'done' },
    ...overrides,
  };
}

describe('fils d’exécution', () => {
  it('montre le fil ouvert, et en diff la sortie qui modifie le code joint', async () => {
    const run = finishedRun();
    useAgents.setState({ runs: [summaryOf(run)], details: { exec_1: run }, openRunId: 'exec_1' });
    wrap(<ThreadView />);
    expect(screen.getByText('✅ Tâche terminée avec OptimizerAgent')).toBeInTheDocument();
    const toggle = screen.getByRole('button', { name: /^Diff/ });
    expect(toggle).toHaveTextContent('+1');
    expect(toggle).toHaveTextContent('−2');
    expect(screen.getByText('print(x)')).toBeInTheDocument();
    // L'onglet Diff ne montre que le code ; l'explication est dans Sortie
    expect(screen.queryByText('Plus de trace.')).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Sortie' }));
    expect(screen.queryByText('print(x)')).toBeNull();
    expect(screen.getByText('Plus de trace.')).toBeInTheDocument();
  });

  it('en parallèle, l’agent que le modèle n’a pas encore servi attend son tour', () => {
    const base = finishedRun().sections[0]!;
    const run = finishedRun({
      kind: 'workflow',
      title: 'Workflow · 2 agents',
      nodes: [
        { id: 0, agent_type: 'security', name: 'SecurityAgent', color: '#ec4899' },
        { id: 1, agent_type: 'optimizer', name: 'OptimizerAgent', color: '#14b8a6' },
      ],
      plan: { mode: 'parallel', steps: [[0, 1]], isolated: [] },
      status: 'running',
      status_text: '',
      finished_at: null,
      duration_ms: null,
      sections: [
        {
          ...base,
          id: 0,
          title: 'SecurityAgent',
          agent_type: 'security',
          color: '#ec4899',
          text: '',
          status: 'running',
          finished_at: null,
        },
        { ...base, id: 1, text: 'Analyse en cours', status: 'running', finished_at: null },
      ],
      node_status: { '0': 'running', '1': 'running' },
    });
    useAgents.setState({ runs: [summaryOf(run)], details: { exec_1: run }, openRunId: 'exec_1' });
    wrap(<ThreadView />);
    expect(screen.getByText('Attend son tour')).toBeInTheDocument();
    expect(
      screen.getByText('Le modèle répond d’abord à OptimizerAgent : cet agent écrira ensuite.'),
    ).toBeInTheDocument();
    expect(screen.getByText('Analyse en cours')).toBeInTheDocument();
  });

  it('rouvre un fil de la liste en le relisant', async () => {
    const older = finishedRun({ id: 'exec_0', title: 'CodeAgent', status: 'error' });
    const newer = finishedRun();
    api.agentRun.mockResolvedValue({ run: older, seq: 7 });
    useAgents.setState({
      runs: [summaryOf(newer), summaryOf(older)],
      details: { exec_1: newer },
      openRunId: 'exec_1',
    });
    wrap(<RunList />);
    const rows = screen.getAllByRole('listitem');
    expect(within(rows[1]!).getByLabelText('Erreur')).toBeInTheDocument();
    await act(async () => {
      await userEvent.click(within(rows[1]!).getAllByRole('button')[0]!);
    });
    expect(useAgents.getState().openRunId).toBe('exec_0');
    expect(api.agentRun).toHaveBeenCalledWith('exec_0');
    await waitFor(() => expect(useAgents.getState().details.exec_0).toEqual(older));
  });
});
