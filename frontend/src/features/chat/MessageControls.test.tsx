import { act, fireEvent, render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import type { ReactNode } from 'react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TooltipProvider } from '../../components/ui/Tooltip';
import type { MessageView } from '../../lib/events';
import { useApp } from '../../stores/app';
import { setDraft, useComposer } from '../../stores/composer';
import { applyTranscript } from '../../stores/voice';
import { Composer } from './Composer';
import { EditDialog } from './EditDialog';
import { StarRating } from './MessageControls';

const actions = vi.hoisted(() => ({
  rateAnswer: vi.fn(() => Promise.resolve(true)),
  editMessage: vi.fn(() => Promise.resolve(true)),
  regenerateAnswer: vi.fn(() => Promise.resolve(true)),
  sendMessage: vi.fn(() => Promise.resolve(true)),
  stopGeneration: vi.fn(() => Promise.resolve()),
  openFile: vi.fn(),
  revealPath: vi.fn(),
  saveToDownloads: vi.fn(),
}));
vi.mock('../../lib/actions', () => actions);

const api = vi.hoisted(() => ({
  toggleDictation: vi.fn(() => Promise.resolve({ state: 'recording' })),
  slashCommands: vi.fn(() => Promise.resolve({ commands: [] })),
  fileLinks: vi.fn(() => Promise.resolve({ links: {} })),
}));
vi.mock('../../lib/api', () => ({ api }));

const wrap = (node: ReactNode) => render(<TooltipProvider>{node}</TooltipProvider>);

const MESSAGE: MessageView = {
  mid: 'u1',
  role: 'user',
  text: 'Explique les tuples\n📎 cours.pdf',
  timestamp: null,
  type: 'text',
  attachments: [{ path: 'C:/cours.pdf', name: 'cours.pdf', type: 'PDF' }],
  image_path: null,
};

beforeEach(() => {
  vi.clearAllMocks();
});

describe('note en étoiles', () => {
  it('se remplit au survol puis enregistre la note', async () => {
    const user = userEvent.setup();
    wrap(<StarRating mid="a1" />);
    const stars = screen.getAllByRole('button', { name: /étoile/ });
    await user.hover(stars[3]!);
    expect(stars.slice(0, 4).every((star) => star.innerHTML.includes('fill-rating'))).toBe(true);
    expect(stars[4]!.innerHTML.includes('fill-rating')).toBe(false);
    await user.click(stars[3]!);
    expect(actions.rateAnswer).toHaveBeenCalledWith('a1', 4);
  });

  it('reste figée une fois notée, comme dans Tk', () => {
    wrap(<StarRating mid="a1" rating={2} />);
    const stars = screen.getAllByRole('button', { name: /étoile/ });
    expect(stars.every((star) => (star as HTMLButtonElement).disabled)).toBe(true);
    expect(screen.getByRole('group', { name: 'Réponse notée 2 sur 5' })).toBeTruthy();
  });
});

describe('modifier un message', () => {
  it("ne fait rien si le texte n'a pas changé, et garde les pièces jointes", async () => {
    const user = userEvent.setup();
    const onClose = vi.fn();
    wrap(<EditDialog message={MESSAGE} hasFollowing={false} onClose={onClose} />);
    const box = screen.getByRole('textbox', { name: 'Message modifié' });
    expect((box as HTMLTextAreaElement).value).toBe('Explique les tuples');
    expect(screen.getByText('Pièces jointes conservées : cours.pdf')).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Regénérer' }));
    expect(actions.editMessage).not.toHaveBeenCalled();
    expect(onClose).toHaveBeenCalled();
  });

  it('régénère avec Ctrl+Entrée', async () => {
    const user = userEvent.setup();
    wrap(<EditDialog message={MESSAGE} hasFollowing={false} onClose={vi.fn()} />);
    const box = screen.getByRole('textbox', { name: 'Message modifié' });
    await user.clear(box);
    await user.type(box, 'Explique les listes');
    await user.keyboard('{Control>}{Enter}{/Control}');
    expect(actions.editMessage).toHaveBeenCalledWith('u1', 'Explique les listes');
  });

  it('demande confirmation quand des messages suivent', async () => {
    const user = userEvent.setup();
    wrap(<EditDialog message={MESSAGE} hasFollowing onClose={vi.fn()} />);
    const box = screen.getByRole('textbox', { name: 'Message modifié' });
    await user.type(box, ' en Python');
    await user.click(screen.getByRole('button', { name: 'Regénérer' }));
    expect(actions.editMessage).not.toHaveBeenCalled();
    expect(screen.getByText(/laisseront place à la nouvelle réponse/)).toBeTruthy();
    await user.click(screen.getByRole('button', { name: 'Continuer' }));
    expect(actions.editMessage).toHaveBeenCalledWith('u1', 'Explique les tuples en Python');
  });
});

describe('saisie vocale', () => {
  it('insère le texte dicté au curseur, avec une espace devant', async () => {
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
    setDraft('Bonjour');
    wrap(<Composer variant="dock" />);
    const box = screen.getByRole<HTMLTextAreaElement>('textbox', { name: 'Message' });
    box.setSelectionRange(7, 7);
    fireEvent.click(screen.getByRole('button', { name: 'Saisie vocale' }));
    await act(async () => {
      await Promise.resolve();
    });
    expect(api.toggleDictation).toHaveBeenCalled();
    act(() => applyTranscript('tout le monde'));
    expect(useComposer.getState().draft).toBe('Bonjour tout le monde');
  });
});
