import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import type { EventPayloads, ServerEvent } from '../../lib/events';
import { applyChatEvents, followNewTurn, resetChat } from '../../stores/chat';
import { Thread } from './Thread';

/** Ce que le fil donne à la liste virtualisée et lui demande */
interface ListProps {
  totalListHeightChanged: (height: number) => void;
  atBottomStateChange: (atBottom: boolean) => void;
  followOutput: (atBottom: boolean) => false | 'auto';
}

// Liste simulée : le test joue react-virtuoso (mesures, bas de la liste)
const list = vi.hoisted(() => ({ props: null as ListProps | null, scrollToIndex: vi.fn() }));
vi.mock('react-virtuoso', async () => {
  const React = await import('react');
  const Virtuoso = React.forwardRef<unknown, Record<string, unknown>>(
    function Virtuoso(props, ref) {
      list.props = props as unknown as ListProps;
      React.useImperativeHandle(ref, () => ({ scrollToIndex: list.scrollToIndex }));
      return null;
    },
  );
  return { Virtuoso };
});

function props(): ListProps {
  if (!list.props) throw new Error('liste non rendue');
  return list.props;
}

let seq = 0;

function userMessage(mid: string, source: EventPayloads['message.user']['source']): ServerEvent {
  seq += 1;
  const payload: EventPayloads['message.user'] = {
    mid,
    request_id: `r-${mid}`,
    text: 'Bonjour',
    source,
    timestamp: '2026-10-15T10:00:00',
    attachments: [],
    image_path: null,
  };
  return { type: 'message.user', payload, conversation_id: 'c1', message_id: mid, seq };
}

/** La réponse en cours grandit : la liste le signale au fil */
function grows() {
  act(() => props().totalListHeightChanged(1000 + seq));
}

beforeEach(() => {
  vi.clearAllMocks();
  resetChat();
  render(<Thread />);
});

describe('fil : défilement collé en bas (chat_area.py de Tk)', () => {
  it('suit la réponse tant que l’utilisateur est en bas', () => {
    grows();
    expect(list.scrollToIndex).toHaveBeenCalledWith({ index: 'LAST', align: 'end' });
    expect(props().followOutput(true)).toBe('auto');
  });

  it('laisse en place un lecteur remonté, puis « ↓ » le ramène et le suivi reprend', () => {
    act(() => props().atBottomStateChange(false));
    grows();
    expect(list.scrollToIndex).not.toHaveBeenCalled();
    expect(props().followOutput(false)).toBe(false);

    fireEvent.click(screen.getByRole('button', { name: 'Revenir en bas' }));
    expect(list.scrollToIndex).toHaveBeenLastCalledWith({
      index: 'LAST',
      align: 'end',
      behavior: 'smooth',
    });
    grows();
    expect(list.scrollToIndex).toHaveBeenLastCalledWith({ index: 'LAST', align: 'end' });
  });

  it('un message envoyé d’ici ramène en bas ; un message du téléphone, non', () => {
    act(() => props().atBottomStateChange(false));
    act(() => applyChatEvents([userMessage('m1', 'mobile')]));
    grows();
    expect(list.scrollToIndex).not.toHaveBeenCalled();

    act(() => followNewTurn()); // envoi, modification ou régénération
    expect(list.scrollToIndex).toHaveBeenCalledWith({ index: 'LAST', align: 'end' });
    list.scrollToIndex.mockClear();
    act(() => applyChatEvents([userMessage('m2', 'desktop')]));
    grows(); // la réponse qui s'écrit est suivie
    expect(list.scrollToIndex).toHaveBeenCalledWith({ index: 'LAST', align: 'end' });
  });
});
