import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { TooltipProvider } from '../../components/ui/Tooltip';
import type { SessionSummary } from '../../lib/events';
import { useApp } from '../../stores/app';
import { Sidebar } from './Sidebar';

const actions = vi.hoisted(() => ({
  renameSession: vi.fn(() => Promise.resolve(true)),
  openSession: vi.fn(() => Promise.resolve()),
  removeSession: vi.fn(() => Promise.resolve()),
  newConversation: vi.fn(() => Promise.resolve()),
  toggleSidebar: vi.fn(),
  setSidebarOpen: vi.fn(),
  exportConversation: vi.fn(() => Promise.resolve()),
}));
vi.mock('../../lib/actions', () => actions);

const SESSIONS: SessionSummary[] = [
  {
    id: 's1',
    name: 'Question A',
    last_modified: '2026-11-12T09:00:00',
    message_count: 2,
    current: true,
  },
  {
    id: 's2',
    name: 'Recette de tarte',
    last_modified: '2026-11-10T18:00:00',
    message_count: 4,
    current: false,
  },
];

const PENCIL = 'Renommer « Question A »';
const FIELD = 'Nouveau nom de la conversation';

function renderSidebar() {
  useApp.setState({ sidebarOpen: true, sessions: SESSIONS });
  return render(
    <TooltipProvider>
      <Sidebar />
    </TooltipProvider>,
  );
}

const field = () => screen.queryByRole('textbox', { name: FIELD });

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('renommer une conversation', () => {
  it('a son crayon juste à gauche de la corbeille', () => {
    renderSidebar();
    const pencil = screen.getByRole('button', { name: PENCIL });
    const trash = screen.getByRole('button', { name: 'Supprimer « Question A »' });
    expect(pencil.nextElementSibling).toBe(trash);
  });

  it('enregistre le nom saisi avec Entrée, puis rend le focus au crayon', async () => {
    const user = userEvent.setup();
    renderSidebar();
    await user.click(screen.getByRole('button', { name: PENCIL }));

    const input = field()!;
    expect(input).toHaveValue('Question A');
    expect(input).toHaveFocus();
    // Tout le nom est sélectionné : la saisie le remplace
    await user.keyboard('  Mon   projet {Enter}');

    expect(actions.renameSession).toHaveBeenCalledWith('s1', 'Mon projet');
    expect(field()).toBeNull();
    expect(screen.getByRole('button', { name: PENCIL })).toHaveFocus();
  });

  it('annule avec Échap, sans arrêter la réponse en cours', async () => {
    const user = userEvent.setup();
    renderSidebar();
    await user.click(screen.getByRole('button', { name: PENCIL }));
    // App.tsx laisse Échap à ce champ (ownsEscape)
    expect(field()).toHaveAttribute('data-own-escape', 'true');

    await user.keyboard('Autre nom{Escape}');

    expect(actions.renameSession).not.toHaveBeenCalled();
    expect(field()).toBeNull();
    expect(screen.getByText('Question A')).toBeInTheDocument();
  });

  it('enregistre aussi quand le champ perd le focus, pas quand la fenêtre le perd', async () => {
    const user = userEvent.setup();
    const hasFocus = vi.spyOn(document, 'hasFocus').mockReturnValue(false);
    renderSidebar();
    await user.click(screen.getByRole('button', { name: PENCIL }));
    await user.keyboard('Projet X');

    // Alt+Tab : le champ attend
    act(() => field()!.blur());
    expect(field()).not.toBeNull();
    expect(actions.renameSession).not.toHaveBeenCalled();

    hasFocus.mockReturnValue(true);
    act(() => field()!.focus());
    act(() => field()!.blur());
    expect(actions.renameSession).toHaveBeenCalledWith('s1', 'Projet X');
    expect(field()).toBeNull();
  });

  it("n'envoie ni un nom vide ni un nom inchangé", async () => {
    const user = userEvent.setup();
    renderSidebar();
    await user.click(screen.getByRole('button', { name: PENCIL }));
    await user.keyboard('{Enter}');
    await user.click(screen.getByRole('button', { name: PENCIL }));
    await user.keyboard('{Backspace}   {Enter}');

    expect(actions.renameSession).not.toHaveBeenCalled();
    expect(screen.getByText('Question A')).toBeInTheDocument();
  });

  it('ne renomme que la conversation de son crayon', async () => {
    const user = userEvent.setup();
    renderSidebar();
    await user.click(screen.getByRole('button', { name: 'Renommer « Recette de tarte »' }));
    expect(field()).toHaveValue('Recette de tarte');
    await user.keyboard('Tarte aux pommes{Enter}');
    expect(actions.renameSession).toHaveBeenCalledWith('s2', 'Tarte aux pommes');
    expect(actions.openSession).not.toHaveBeenCalled();
  });
});
