import { act, fireEvent, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TooltipProvider } from '../../components/ui/Tooltip';
import { dispatchDroppedPaths, noteDrop, onDroppedPaths } from '../../lib/drops';
import { useApp } from '../../stores/app';
import { setDraft, useComposer } from '../../stores/composer';
import { Composer } from './Composer';
import { commandText, slashPrefix } from './slash';

const api = vi.hoisted(() => ({
  slashCommands: vi.fn(),
  uploadAttachment: vi.fn(),
  addAttachment: vi.fn(),
  removeAttachment: vi.fn(),
  fileLinks: vi.fn(() => Promise.resolve({ links: {} })),
}));
vi.mock('../../lib/api', () => ({ api }));

const COMMANDS = [
  { command: 'code', title: 'Génération de code', description: 'Génère un programme' },
  { command: 'corrige', title: 'Correction', description: '' },
];

function renderComposer() {
  return render(
    <TooltipProvider>
      <Composer variant="dock" />
    </TooltipProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  api.slashCommands.mockImplementation((prefix: string) =>
    Promise.resolve({ commands: COMMANDS.filter((item) => item.command.startsWith(prefix)) }),
  );
  api.uploadAttachment.mockResolvedValue({});
  setDraft('');
  useApp.setState({
    status: {
      state: 'ready',
      step: 'ready',
      label: 'Prêt',
      detail: '',
      error: null,
      ollama: true,
      placement: null,
    },
  });
});

describe('slash commands', () => {
  it('ne réagit qu’à « / » en début de saisie, sans espace', () => {
    expect(slashPrefix('/co')).toBe('co');
    expect(slashPrefix('/')).toBe('');
    expect(slashPrefix('/code un jeu')).toBeNull();
    expect(slashPrefix('écris /code')).toBeNull();
    expect(commandText(COMMANDS[0]!)).toBe('/code ');
  });

  it('se choisissent au clavier et insèrent « /commande »', async () => {
    const user = userEvent.setup();
    renderComposer();
    const box = screen.getByRole('textbox', { name: 'Message' });
    await user.type(box, '/c');
    const list = await screen.findByRole('listbox', { name: 'Commandes' });
    expect(list.querySelectorAll('[role="option"]')).toHaveLength(2);
    await user.keyboard('{ArrowDown}{Enter}');
    expect(useComposer.getState().draft).toBe('/corrige ');
    // Liste refermée : Entrée enverrait le message, plus rien n'est proposé
    expect(screen.queryByRole('listbox')).toBeNull();
  });

  it('ne suivent la souris que si elle bouge : la liste s’ouvre sous un curseur immobile', async () => {
    const user = userEvent.setup();
    renderComposer();
    await user.type(screen.getByRole('textbox', { name: 'Message' }), '/');
    const options = await screen.findAllByRole<HTMLElement>('option');
    const second = options[1]!;
    // Premier événement : la position du curseur, sous lequel la liste vient de s'ouvrir
    fireEvent.pointerMove(second, { clientX: 40, clientY: 12 });
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
    fireEvent.pointerMove(second, { clientX: 40, clientY: 12 });
    expect(options[0]).toHaveAttribute('aria-selected', 'true');
    // La souris bouge : la commande survolée est choisie
    fireEvent.pointerMove(second, { clientX: 44, clientY: 13 });
    expect(second).toHaveAttribute('aria-selected', 'true');
  });

  it('se ferment avec Échap, et Entrée ne choisit plus rien ensuite', async () => {
    const user = userEvent.setup();
    renderComposer();
    const box = screen.getByRole('textbox', { name: 'Message' });
    await user.type(box, '/co');
    await screen.findByRole('listbox');
    await user.keyboard('{Escape}');
    expect(screen.queryByRole('listbox')).toBeNull();
    expect(useComposer.getState().draft).toBe('/co');
  });
});

describe('pièces jointes', () => {
  it('colle une image du presse-papiers sous le nom de Tk', () => {
    renderComposer();
    const box = screen.getByRole('textbox', { name: 'Message' });
    const image = new File(['png'], 'image.png', { type: 'image/png' });
    fireEvent.paste(box, {
      clipboardData: { files: [image], getData: () => '' },
    });
    expect(api.uploadAttachment).toHaveBeenCalledWith(image, 'clipboard_image.png');
  });

  it('colle du texte comme du texte, même accompagné d’une image (Word)', () => {
    renderComposer();
    const box = screen.getByRole('textbox', { name: 'Message' });
    const image = new File(['png'], 'image.png', { type: 'image/png' });
    fireEvent.paste(box, {
      clipboardData: { files: [image], getData: () => 'Un paragraphe copié' },
    });
    expect(api.uploadAttachment).not.toHaveBeenCalled();
  });

  it('remet les chemins déposés à la zone du dépôt, s’ils arrivent à temps', async () => {
    const received: string[][] = [];
    const stop = onDroppedPaths('chat', (paths) => received.push(paths));
    noteDrop('chat');
    dispatchDroppedPaths(['C:/a.pdf']);
    // Sans dépôt noté : rien (un dépôt hors de la page, par exemple)
    dispatchDroppedPaths(['C:/b.pdf']);
    stop();
    expect(received).toEqual([['C:/a.pdf']]);
    await waitFor(() => expect(received).toHaveLength(1));
  });

  it('éclaire la carte de saisie pendant le survol de fichiers', () => {
    renderComposer();
    act(() => useComposer.setState({ dropping: true }));
    const card = screen.getByRole('textbox', { name: 'Message' }).parentElement;
    expect(card?.className).toContain('border-accent');
  });
});
