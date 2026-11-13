import { render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { TooltipProvider } from '../../components/ui/Tooltip';
import type { CodeMessage, MessageView } from '../../lib/events';
import { useApp } from '../../stores/app';
import { useChat } from '../../stores/chat';
import { useCode } from '../../stores/code';
import { Header } from './Header';

vi.mock('../../lib/actions', () => ({ toggleSidebar: vi.fn() }));

const MESSAGE: MessageView = {
  mid: 'u1',
  role: 'user',
  text: 'Bonjour',
  timestamp: null,
  type: 'text',
  attachments: [],
  image_path: null,
};

const renderHeader = () =>
  render(
    <TooltipProvider>
      <Header />
    </TooltipProvider>,
  );

beforeEach(() => {
  useApp.setState({ tab: 'chat', sidebarOpen: true });
  useChat.setState({ messages: [MESSAGE] });
  useCode.setState({ messages: [] });
});

describe('en-tête', () => {
  it('n’a pas de corbeille dans une conversation du chat, seulement l’aide', () => {
    renderHeader();
    expect(screen.getByRole('button', { name: 'Aide' })).toBeInTheDocument();
    // « Nouvelle conversation » (barre latérale, Ctrl+N) fait déjà ce qu'elle faisait
    expect(screen.queryByRole('button', { name: /conversation/i })).toBeNull();
  });

  it('garde celle de la page Code, seule à effacer la conversation de VS Code', () => {
    useApp.setState({ tab: 'code' });
    useCode.setState({ messages: [{} as CodeMessage] });
    renderHeader();
    expect(screen.getByRole('button', { name: /Nouvelle conversation Code/ })).toBeInTheDocument();
  });
});
