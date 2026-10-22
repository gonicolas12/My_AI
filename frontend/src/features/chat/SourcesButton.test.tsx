import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TooltipProvider } from '../../components/ui/Tooltip';
import type { MessageView } from '../../lib/events';
import { installNavigationGuard, shell } from '../../lib/shell';
import { AssistantMessage } from './AssistantMessage';

const toggleSpeak = vi.hoisted(() => vi.fn(() => Promise.resolve()));
vi.mock('../../stores/voice', async (importOriginal) => ({
  ...(await importOriginal<typeof import('../../stores/voice')>()),
  toggleSpeak,
}));

const ANSWER = 'La population atteint 8,3 milliards [1], en hausse de 0,8 % [4].';

const MESSAGE: MessageView = {
  mid: 'a1',
  role: 'assistant',
  text: [
    ANSWER,
    '',
    '📚 **Sources**',
    '[1] [Population mondiale — Wikipédia](https://fr.wikipedia.org/wiki/Population_mondiale)',
    '[4] [Démographie mondiale 2026](https://www.worldometers.info/fr/demographie/)',
    '[5] [Population mondiale : projection](https://www.ined.fr/fr/projections/)',
    '[7] [Combien sommes-nous ?](https://www.quebecscience.qc.ca/population/)',
  ].join('\n'),
  timestamp: null,
  type: 'text',
  attachments: [],
  image_path: null,
  tokens_per_s: 15.9,
};

describe('sources d’une réponse appuyée sur une recherche web', () => {
  it('quittent le texte pour le bouton Sources, à droite des tokens/s', async () => {
    const user = userEvent.setup();
    render(
      <TooltipProvider>
        <AssistantMessage message={MESSAGE} isLast />
      </TooltipProvider>,
    );

    // Le texte garde ses citations cliquables, plus la liste qui le terminait
    expect(screen.queryByText(/📚|Wikipédia/)).toBeNull();
    expect(screen.getByRole('link', { name: '[1]' })).toHaveAttribute(
      'href',
      'https://fr.wikipedia.org/wiki/Population_mondiale',
    );

    // Bouton après la ligne d'infos, avec les icônes des trois premières sources
    const button = screen.getByRole('button', { name: 'Sources (4)' });
    expect(screen.getByText('15,9 tokens/s').nextElementSibling).toBe(button);
    expect([...button.querySelectorAll('img')].map((img) => img.getAttribute('src'))).toEqual([
      '/api/favicon?host=fr.wikipedia.org',
      '/api/favicon?host=www.worldometers.info',
      '/api/favicon?host=www.ined.fr',
    ]);

    // La liste : toutes les sources, en liens, chacune avec l'icône de son site
    await user.click(button);
    const items = screen.getAllByRole('menuitem');
    expect(items.map((item) => [item.textContent, item.getAttribute('href')])).toEqual([
      ['Population mondiale — Wikipédia', 'https://fr.wikipedia.org/wiki/Population_mondiale'],
      ['Démographie mondiale 2026', 'https://www.worldometers.info/fr/demographie/'],
      ['Population mondiale : projection', 'https://www.ined.fr/fr/projections/'],
      ['Combien sommes-nous ?', 'https://www.quebecscience.qc.ca/population/'],
    ]);
    expect(items.every((item) => item.querySelector('img'))).toBe(true);
  });

  it('ouvrent leur page dans le navigateur du système, à la souris comme au clavier', async () => {
    const user = userEvent.setup();
    const open = vi.spyOn(shell, 'openExternal').mockResolvedValue(true);
    const removeGuard = installNavigationGuard();
    render(
      <TooltipProvider>
        <AssistantMessage message={MESSAGE} isLast />
      </TooltipProvider>,
    );
    const button = screen.getByRole('button', { name: 'Sources (4)' });

    await user.click(button);
    await user.click(screen.getByRole('menuitem', { name: 'Démographie mondiale 2026' }));
    expect(open).toHaveBeenLastCalledWith('https://www.worldometers.info/fr/demographie/');
    expect(screen.queryByRole('menu')).toBeNull();

    // Entrée ouvre la liste sur la première source, Flèche bas passe à la suivante
    button.focus();
    await user.keyboard('{Enter}');
    await user.keyboard('{ArrowDown}{Enter}');
    expect(open).toHaveBeenLastCalledWith('https://www.worldometers.info/fr/demographie/');
    expect(open).toHaveBeenCalledTimes(2);
    removeGuard();
  });

  it('ne lisent pas la liste à voix haute', async () => {
    const user = userEvent.setup();
    render(
      <TooltipProvider>
        <AssistantMessage message={MESSAGE} isLast />
      </TooltipProvider>,
    );
    await user.click(screen.getByRole('button', { name: 'Lire à voix haute' }));
    expect(toggleSpeak).toHaveBeenCalledWith(ANSWER, 'a1');
  });

  it("n'apparaissent pas sans recherche web", () => {
    render(
      <TooltipProvider>
        <AssistantMessage message={{ ...MESSAGE, text: ANSWER }} isLast />
      </TooltipProvider>,
    );
    expect(screen.queryByRole('button', { name: /^Sources/ })).toBeNull();
  });
});
