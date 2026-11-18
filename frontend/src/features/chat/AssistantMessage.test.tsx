import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TooltipProvider } from '../../components/ui/Tooltip';
import type { MessageView } from '../../lib/events';
import { usePreview } from '../../stores/preview';
import { AssistantMessage } from './AssistantMessage';

const showInMemory = vi.hoisted(() => vi.fn());
vi.mock('../../stores/memory', () => ({ showInMemory }));

const MESSAGE: MessageView = {
  mid: 'a1',
  role: 'assistant',
  text: 'Ton dossier OneDrive ne contient que `desktop.ini`.',
  timestamp: null,
  type: 'text',
  attachments: [],
  image_path: null,
};

describe('dossier de la Mémoire au nom proche de celui de la question', () => {
  it('signalé sous la réponse qui ne le cite pas ; un clic ouvre la Mémoire sur lui', async () => {
    const user = userEvent.setup();
    render(
      <TooltipProvider>
        <AssistantMessage
          message={{ ...MESSAGE, memory_near: [{ name: 'OneDrive_3_06-10-2026', files: 2 }] }}
          isLast
        />
      </TooltipProvider>,
    );
    expect(screen.getByText('Aussi dans la Mémoire :')).toBeInTheDocument();
    const folder = screen.getByRole('button', { name: /OneDrive_3_06-10-2026/ });
    expect(folder).toHaveTextContent('OneDrive_3_06-10-2026(2 fichiers)');
    expect(folder).toHaveAttribute('title', 'Voir « OneDrive_3_06-10-2026 » dans la Mémoire');
    await user.click(folder);
    expect(showInMemory).toHaveBeenCalledWith('OneDrive_3_06-10-2026');
  });

  it('rien sans dossier proche', () => {
    render(
      <TooltipProvider>
        <AssistantMessage message={MESSAGE} isLast />
      </TooltipProvider>,
    );
    expect(screen.queryByText('Aussi dans la Mémoire :')).toBeNull();
  });
});

describe('aperçus d’une réponse', () => {
  const ANSWER: MessageView = {
    ...MESSAGE,
    text: [
      'Voici la page :',
      '',
      '```html',
      '<h1>Bonjour</h1>',
      '```',
      '',
      'Et un script :',
      '',
      '```python',
      'print(1)',
      '```',
      '',
      'Puis le logo :',
      '',
      '```svg',
      '<svg viewBox="0 0 10 10"><circle r="4"/></svg>',
      '```',
    ].join('\n'),
    documents: ['C:/out/rapport.pdf'],
  };

  it('chaque bloc HTML ou SVG a son bouton « Aperçu » ; plus de bouton sous la réponse', async () => {
    const user = userEvent.setup();
    usePreview.setState({ open: false, closing: false, items: [], index: 0 });
    render(
      <TooltipProvider>
        <AssistantMessage message={ANSWER} isLast />
      </TooltipProvider>,
    );
    const buttons = screen.getAllByRole('button', { name: 'Afficher l’aperçu de ce bloc' });
    // Le bloc HTML et le SVG, pas le Python
    expect(buttons).toHaveLength(2);
    expect(screen.queryByRole('button', { name: /^Aperçu \(\d+\)$/ })).not.toBeInTheDocument();
    await user.click(buttons[1]!);
    const state = usePreview.getState();
    expect(state.open).toBe(true);
    // Le volet s'ouvre sur le SVG, les autres aperçus de la réponse s'y suivent
    expect(state.index).toBe(1);
    expect(state.items.map((item) => item.kind)).toEqual(['html', 'svg', 'document']);
  });

  it('une réponse sans bloc HTML ni SVG n’a aucun bouton d’aperçu de bloc', () => {
    render(
      <TooltipProvider>
        <AssistantMessage message={{ ...MESSAGE, documents: ['C:/out/rapport.pdf'] }} isLast />
      </TooltipProvider>,
    );
    expect(screen.queryByRole('button', { name: 'Afficher l’aperçu de ce bloc' })).toBeNull();
    // Le document garde sa carte, qui ouvre le volet
    expect(screen.getByRole('button', { name: 'Aperçu de rapport.pdf' })).toBeInTheDocument();
  });
});
