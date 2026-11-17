import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, expect, it, vi } from 'vitest';

import { TooltipProvider } from '../../components/ui/Tooltip';
import type { MessageView } from '../../lib/events';
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
