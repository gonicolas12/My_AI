import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TooltipProvider } from '../../components/ui/Tooltip';
import type { AgentInfo, RunView } from '../../lib/events';
import { resetAgents, useAgents } from '../../stores/agents';
import { useApp } from '../../stores/app';
import { summaryOf } from '../../stores/agentsReducer';
import { resetResources, useResources } from '../../stores/resources';
import { AgentDialog } from './AgentDialog';
import { AgentGrid } from './AgentGrid';
import { resetWorkflow, useWorkflow } from './canvas/workflowStore';
import { DebateDialog } from './DebateDialog';
import { RunList } from './runs/RunList';
import { ThreadView } from './runs/ThreadView';
import { StatsPanel } from './stats/StatsPanel';
import { TaskZone } from './TaskZone';

const api = vi.hoisted(() => ({
  agents: vi.fn(),
  createAgent: vi.fn(),
  editAgent: vi.fn(),
  deleteAgent: vi.fn(),
  agentRun: vi.fn(),
  stopRun: vi.fn(),
  startDebate: vi.fn(),
  fileLinks: vi.fn(() => Promise.resolve({ links: {} })),
}));
vi.mock('../../lib/api', () => ({
  api,
  faviconUrl: (host: string) => `/api/favicon?host=${host}`,
}));

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
  resetResources();
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
  it('Ctrl+Entrée exécute, Débat ouvre son dialogue, Vider vide le canvas', async () => {
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
    wrap(<TaskZone onExecute={onExecute} onDebateStarted={vi.fn()} />);
    const task = screen.getByRole('textbox', { name: 'Tâche' });
    await userEvent.type(task, 'Écris un tri');
    fireEvent.keyDown(task, { key: 'Enter', ctrlKey: true });
    expect(onExecute).toHaveBeenCalledTimes(1);
    expect(useAgents.getState().task).toBe('Écris un tri');
    await userEvent.click(screen.getByRole('button', { name: 'Débat' }));
    const dialog = await screen.findByRole('dialog', { name: 'Mode Débat entre deux agents' });
    await userEvent.click(within(dialog).getByRole('button', { name: 'Annuler' }));
    await userEvent.click(screen.getByRole('button', { name: 'Vider' }));
    expect(useWorkflow.getState().nodes).toHaveLength(0);
  });

  it('pendant une exécution, Exécuter devient Arrêter', async () => {
    api.stopRun.mockResolvedValue({ stopped: true });
    useAgents.setState({ active: 'exec_1' });
    wrap(<TaskZone onExecute={vi.fn()} onDebateStarted={vi.fn()} />);
    expect(screen.queryByRole('button', { name: 'Exécuter' })).toBeNull();
    await userEvent.click(screen.getByRole('button', { name: 'Arrêter' }));
    expect(api.stopRun).toHaveBeenCalledWith('exec_1');
  });

  it('pendant une exécution venue du téléphone, Exécuter attend et Débat refuse', async () => {
    const phone = finishedRun({ id: 'exec_phone', origin: 'mobile', status: 'running' });
    useAgents.setState({
      active: 'exec_phone',
      busy: true,
      runs: [summaryOf(phone)],
      details: { exec_phone: phone },
    });
    wrap(<TaskZone onExecute={vi.fn()} onDebateStarted={vi.fn()} />);
    expect(screen.queryByRole('button', { name: 'Arrêter' })).toBeNull();
    expect(screen.getByRole('button', { name: 'Exécuter' })).toBeDisabled();
    await userEvent.click(screen.getByRole('button', { name: 'Débat' }));
    expect(screen.queryByRole('dialog')).toBeNull();
    expect(useApp.getState().toasts.at(-1)?.message).toBe('⏳ Une tâche est déjà en cours');
  });
});

function finishedRun(overrides: Partial<RunView> = {}): RunView {
  return {
    id: 'exec_1',
    kind: 'agent',
    origin: 'desktop',
    title: 'OptimizerAgent',
    task: 'Optimise ce code',
    attachments: [{ path: 'C:/p/utils.py', name: 'utils.py', type: 'Code' }],
    sources: [{ name: 'utils.py', text: 'def f(x):\n    print(x)\n    return x == None\n' }],
    nodes: [{ id: 0, agent_type: 'optimizer', name: 'OptimizerAgent', color: '#14b8a6' }],
    connections: [],
    plan: { mode: 'single', steps: [[0]], isolated: [] },
    debate: null,
    schedule: null,
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

  it('rend cliquables les liens d’une sortie : citations du WebAgent, adresses nues, tableaux ; ses sources passent sous le bouton Sources', async () => {
    // Les sources du WebAgent s'affichaient en texte brut dans Tk (output_rendering.py),
    // et ses marqueurs [n] restaient du texte alors que le chat les rend cliquables
    const base = finishedRun().sections[0]!;
    const run = finishedRun({
      title: 'WebAgent',
      attachments: [],
      sources: [],
      sections: [
        {
          ...base,
          title: 'WebAgent',
          agent_type: 'web',
          text: [
            '**Toyota** reste *fiable* [1] : `98/100`, voir https://example.org/b.',
            '',
            '| Marque | Source |',
            '|---|---|',
            '| Toyota [2] | voir [OCU](https://www.autosblog.fr/ocu/) |',
            '',
            '📚 **Sources**',
            '[1] [Marques fiables 2026](https://www.autosblog.fr/marques/)',
            '[2] [Fiabilité OCU](https://automedias.fr/voiture-fiable/)',
          ].join('\n'),
        },
      ],
    });
    useAgents.setState({ runs: [summaryOf(run)], details: { exec_1: run }, openRunId: 'exec_1' });
    wrap(<ThreadView />);
    const links = screen.getAllByRole('link');
    expect(links.map((link) => [link.textContent, link.getAttribute('href')])).toEqual([
      ['[1]', 'https://www.autosblog.fr/marques/'],
      ['https://example.org/b', 'https://example.org/b'],
      ['[2]', 'https://automedias.fr/voiture-fiable/'],
      ['OCU', 'https://www.autosblog.fr/ocu/'],
    ]);
    // Marqueurs [n] : même lien bleu que dans le chat (md-cite)
    const cites = links.filter((link) => /^\[\d\]$/.test(link.textContent ?? ''));
    expect(cites.every((link) => link.classList.contains('md-cite'))).toBe(true);
    // Liens ouverts dans le navigateur du système, jamais dans la fenêtre
    expect(links.every((link) => link.getAttribute('target') === '_blank')).toBe(true);
    expect(within(screen.getByRole('table')).getByRole('link', { name: 'OCU' })).toBeVisible();
    // Gras, italique et code gardent leur texte, sans balisage
    expect(screen.getByText('Toyota', { selector: 'strong' })).toBeInTheDocument();
    expect(screen.getByText('fiable', { selector: 'em' })).toBeInTheDocument();
    expect(screen.getByText('98/100', { selector: 'code' })).toBeInTheDocument();

    // Le bloc 📚 Sources quitte la sortie : bouton Sources, icônes des sites en tête
    expect(screen.queryByText(/Sources\*\*|📚/)).toBeNull();
    const button = screen.getByRole('button', { name: 'Sources (2)' });
    expect([...button.querySelectorAll('img')].map((img) => img.getAttribute('src'))).toEqual([
      '/api/favicon?host=www.autosblog.fr',
      '/api/favicon?host=automedias.fr',
    ]);
    await userEvent.click(button);
    const items = screen.getAllByRole('menuitem');
    expect(items.map((item) => [item.textContent, item.getAttribute('href')])).toEqual([
      ['Marques fiables 2026', 'https://www.autosblog.fr/marques/'],
      ['Fiabilité OCU', 'https://automedias.fr/voiture-fiable/'],
    ]);
    expect(items.every((item) => item.querySelector('img'))).toBe(true);
  });

  it('montre la recherche du WebAgent hors de sa sortie, le temps qu’il écrive', () => {
    // « 🔍 Recherche terminée » s'écrivait dans la sortie et y restait
    const base = finishedRun().sections[0]!;
    const run = finishedRun({
      title: 'WebAgent',
      attachments: [],
      sources: [],
      status: 'running',
      status_text: '',
      finished_at: null,
      duration_ms: null,
      sections: [{ ...base, title: 'WebAgent', agent_type: 'web', text: '', status: 'running' }],
    });
    useAgents.setState({ runs: [summaryOf(run)], details: { exec_1: run }, openRunId: 'exec_1' });
    wrap(<ThreadView />);
    expect(screen.getByText('L’agent cherche sur internet…')).toBeInTheDocument();
    expect(screen.queryByText('L’agent rédige sa réponse…')).toBeNull();
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

  it('dit l’origine d’un fil, mène à son rapport et donne la vitesse de chaque agent', () => {
    const base = finishedRun().sections[0]!;
    const run = finishedRun({
      origin: 'scheduled',
      title: 'Veille du matin',
      schedule: { task_id: 'sched_1', name: 'Veille du matin', output_file: 'C:/out/rapport.md' },
      sections: [{ ...base, tokens_per_sec: 41.5 }],
    });
    useAgents.setState({ runs: [summaryOf(run)], details: { exec_1: run }, openRunId: 'exec_1' });
    wrap(<ThreadView />);
    expect(screen.getByText('Tâche planifiée')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Rapport' })).toHaveAttribute(
      'title',
      'C:/out/rapport.md',
    );
    expect(screen.getByText(/41,5 tok\/s/)).toBeInTheDocument();
  });

  it('résume un débat : proposant, opposant, tours', () => {
    const run = finishedRun({
      kind: 'debate',
      title: 'Débat · CodeAgent vs DebugAgent',
      task: 'Tabs ou espaces ?',
      sources: [],
      nodes: [
        { id: 'a', agent_type: 'code', name: 'CodeAgent', color: '#3b82f6' },
        { id: 'b', agent_type: 'debug', name: 'DebugAgent', color: '#ef4444' },
      ],
      plan: { mode: 'debate', steps: [], isolated: [] },
      debate: { agent_a: 'code', agent_b: 'debug', rounds: 2 },
      sections: [
        { ...finishedRun().sections[0]!, id: 'deb_1', title: 'Tour 1 — CodeAgent (Proposant)' },
      ],
      status_text: '✅ Débat terminé (2 tours)',
    });
    useAgents.setState({ runs: [summaryOf(run)], details: { exec_1: run }, openRunId: 'exec_1' });
    wrap(<ThreadView />);
    expect(
      screen.getByText('Proposant : CodeAgent · Opposant : DebugAgent · 2 tours'),
    ).toBeInTheDocument();
    expect(screen.getByText('Tour 1 — CodeAgent (Proposant)')).toBeInTheDocument();
  });
});

describe('dialogue du débat', () => {
  it('reprend les contrôles de Tk, puis lance le débat', async () => {
    api.startDebate.mockResolvedValue({ run_id: 'exec_9' });
    const onClose = vi.fn();
    const onStarted = vi.fn();
    wrap(<DebateDialog onClose={onClose} onStarted={onStarted} />);
    const start = screen.getByRole('button', { name: 'Démarrer le débat' });
    await userEvent.selectOptions(screen.getByLabelText('Agent B — Opposant'), 'code');
    await userEvent.click(start);
    expect(screen.getByText('❌ Choisis deux agents différents')).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText('Agent B — Opposant'), 'debug');
    await userEvent.click(start);
    expect(screen.getByText('❌ Sujet requis')).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText('Sujet du débat'), 'Tabs ou espaces ?');
    const rounds = screen.getByLabelText('Nombre de tours :');
    await userEvent.clear(rounds);
    await userEvent.type(rounds, '12');
    await userEvent.click(start);
    await waitFor(() => expect(onStarted).toHaveBeenCalledWith('exec_9'));
    // Tours ramenés entre 1 et 10, comme Tk
    expect(api.startDebate).toHaveBeenCalledWith('code', 'debug', 'Tabs ou espaces ?', 10);
    expect(onClose).toHaveBeenCalled();
  });

  it('montre le refus du serveur et reste ouvert', async () => {
    api.startDebate.mockRejectedValue(new Error('⏳ Une tâche est déjà en cours'));
    const onClose = vi.fn();
    wrap(<DebateDialog onClose={onClose} onStarted={vi.fn()} />);
    await userEvent.type(screen.getByLabelText('Sujet du débat'), 'Sujet');
    await userEvent.click(screen.getByRole('button', { name: 'Démarrer le débat' }));
    expect(await screen.findByText('⏳ Une tâche est déjà en cours')).toBeInTheDocument();
    expect(onClose).not.toHaveBeenCalled();
  });
});

describe('statistiques et ressources', () => {
  it('montre les trois chiffres et les six barres de Tk', () => {
    useAgents.setState({ stats: { tasks: 7, agents: 3, success_rate: 86 } });
    useResources.setState({
      metrics: {
        cpu_percent: 12.3,
        ram_used_mb: 2900,
        ram_total_mb: 16000,
        ram_percent: 18.1,
        gpu_available: true,
        gpu_percent: 86,
        gpu_mem_used_mb: 3700,
        gpu_mem_total_mb: 6144,
        inference_ms: 1840,
        tokens_per_sec: 41.5,
      },
      history: { cpu: [4, 12.3], ram: [2900, 2900], gpu: [30, 86], tps: [38, 41.5] },
      inferences: 2,
      loaded: true,
    });
    wrap(<StatsPanel />);
    expect(screen.getByText('Tâches exécutées').nextSibling).toHaveTextContent('7');
    expect(screen.getByText('Agents actifs').nextSibling).toHaveTextContent('3');
    expect(screen.getByText('Taux de succès').nextSibling).toHaveTextContent('86 %');
    const meters = screen.getAllByRole('meter');
    expect(meters.map((meter) => meter.getAttribute('aria-label'))).toEqual([
      'CPU',
      'RAM',
      'GPU',
      'VRAM',
      'Temps inférence',
      'Tokens/sec',
    ]);
    expect(meters[2]).toHaveAttribute('aria-valuenow', '86');
    expect(meters[5]).toHaveAttribute('aria-valuetext', '41,5 tok/s');
  });

  it('attend la première mesure, et sans fil terminé n’invente pas de taux', () => {
    wrap(<StatsPanel />);
    expect(screen.getByText('Première mesure…')).toBeInTheDocument();
    expect(screen.getByText('Taux de succès').nextSibling).toHaveTextContent('—');
  });
});
