import { act, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import { useApp } from '../../stores/app';
import { togglePalette, usePalette } from '../../stores/palette';
import { usePanels } from '../../stores/panels';
import { CommandPalette } from './CommandPalette';
import { filterCommands, PALETTE_COMMANDS } from './commands';

const api = vi.hoisted(() => ({
  newConversation: vi.fn(() => Promise.resolve({})),
  saveUiState: vi.fn(() => Promise.resolve({})),
}));
vi.mock('../../lib/api', () => ({ api }));

beforeAll(() => {
  // cmdk mesure sa liste et fait défiler l'élément choisi : absents de jsdom
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
  Object.defineProperty(Element.prototype, 'scrollIntoView', {
    configurable: true,
    writable: true,
    value: () => undefined,
  });
});

beforeEach(() => {
  vi.clearAllMocks();
  usePalette.setState({ open: false });
  usePanels.setState({ open: null });
  useApp.setState({ tab: 'chat', sidebarOpen: false });
});

describe('filterCommands', () => {
  it('garde les 14 commandes de Tk, dans son ordre', () => {
    expect(PALETTE_COMMANDS).toHaveLength(14);
    expect(PALETTE_COMMANDS[0]?.label).toBe('Nouveau chat');
    expect(PALETTE_COMMANDS.at(-1)?.label).toBe('Aide');
  });

  it('cherche une sous-chaîne du libellé ou du raccourci, sans casse', () => {
    const labels = (query: string) =>
      filterCommands(PALETTE_COMMANDS, query).map((command) => command.label);
    expect(labels('  EXPORT ')).toEqual([
      'Exporter la conversation (Markdown)',
      'Exporter la conversation (HTML)',
      'Exporter la conversation (PDF)',
    ]);
    expect(labels('ctrl+r')).toEqual(['Relay (accès mobile)']);
    expect(labels('f1')).toEqual(['Aide']);
    expect(labels('')).toHaveLength(14);
    expect(labels('introuvable')).toEqual([]);
  });
});

describe('CommandPalette', () => {
  it('filtre, choisit au clavier en boucle, exécute après fermeture', async () => {
    const user = userEvent.setup();
    render(<CommandPalette />);
    act(() => togglePalette());

    const input = await screen.findByRole('combobox');
    expect(screen.getAllByRole('option')).toHaveLength(14);
    expect(screen.getByRole('option', { name: /Nouveau chat/ })).toHaveAttribute(
      'aria-selected',
      'true',
    );

    await user.type(input, 'mé');
    expect(screen.getAllByRole('option').map((option) => option.textContent)).toEqual(['Mémoire']);
    await user.clear(input);
    await user.type(input, 'onglet');
    // Flèche haute depuis la première : la dernière (boucle)
    await user.keyboard('{ArrowUp}');
    expect(screen.getByRole('option', { name: /onglet Agents/ })).toHaveAttribute(
      'aria-selected',
      'true',
    );
    await user.keyboard('{Enter}');
    expect(usePalette.getState().open).toBe(false);
    expect(useApp.getState().tab).toBe('agents');
  });

  it('ouvre un panneau, la barre latérale revient avec l’onglet Chat', async () => {
    const user = userEvent.setup();
    render(<CommandPalette />);
    act(() => togglePalette());
    await user.type(await screen.findByRole('combobox'), 'prompts');
    await user.keyboard('{Enter}');
    expect(usePanels.getState().open).toBe('prompts');

    useApp.setState({ tab: 'agents', sidebarOpen: false });
    act(() => togglePalette());
    await user.type(await screen.findByRole('combobox'), 'ctrl+b');
    await user.keyboard('{Enter}');
    expect(useApp.getState()).toMatchObject({ tab: 'chat', sidebarOpen: true });
  });

  it('Échap la ferme ; rouverte, la recherche est vide', async () => {
    const user = userEvent.setup();
    render(<CommandPalette />);
    act(() => togglePalette());
    await user.type(await screen.findByRole('combobox'), 'aide');
    await user.keyboard('{Escape}');
    expect(usePalette.getState().open).toBe(false);
    act(() => togglePalette());
    expect(await screen.findByRole('combobox')).toHaveValue('');
  });
});
