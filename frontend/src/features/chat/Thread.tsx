/*
 * Fil de messages : liste virtualisée (react-virtuoso), colonne de lecture
 * centrée. Le défilement reste collé en bas pendant une réponse, sauf si
 * l'utilisateur est remonté : le bouton « ↓ » le ramène alors en bas.
 */

import { ArrowDown } from 'lucide-react';
import { useCallback, useMemo, useRef, useState } from 'react';
import { Virtuoso, type VirtuosoHandle } from 'react-virtuoso';

import type { MessageView } from '../../lib/events';
import { useChat } from '../../stores/chat';
import { isGenerating, type LiveTurn, type PendingTurn } from '../../stores/chatReducer';
import { AssistantMessage } from './AssistantMessage';
import { UserMessage } from './UserMessage';

type ThreadItem =
  | { kind: 'message'; message: MessageView }
  | { kind: 'live'; live: LiveTurn | null; pending: PendingTurn | null };

function itemKey(_index: number, item: ThreadItem): string {
  if (item.kind === 'message') return item.message.mid;
  // Même clé que le message terminé : pas de remontage à la fin de la réponse
  return item.live?.mid ?? `pending-${item.pending?.mid ?? ''}`;
}

/** Hauteur sous laquelle on considère être en bas (px) */
const BOTTOM_THRESHOLD = 96;

export function Thread() {
  const messages = useChat((state) => state.messages);
  const live = useChat((state) => state.live);
  const pending = useChat((state) => state.pending);
  const branches = useChat((state) => state.branches);
  const conversationId = useChat((state) => state.conversationId);
  const busy = useChat(isGenerating);
  const virtuoso = useRef<VirtuosoHandle>(null);
  const [atBottom, setAtBottom] = useState(true);
  const stick = useRef(true);

  const items = useMemo<ThreadItem[]>(() => {
    const list: ThreadItem[] = messages.map((message) => ({ kind: 'message', message }));
    if (live || pending) list.push({ kind: 'live', live, pending });
    return list;
  }, [messages, live, pending]);

  const lastIndex = items.length - 1;

  const onBottom = useCallback((bottom: boolean) => {
    stick.current = bottom;
    setAtBottom(bottom);
  }, []);

  // La réponse en cours grandit sans ajouter d'élément : rester en bas
  const onHeightChange = useCallback(() => {
    if (stick.current) virtuoso.current?.scrollToIndex({ index: 'LAST', align: 'end' });
  }, []);

  const scrollToBottom = () => {
    stick.current = true;
    virtuoso.current?.scrollToIndex({ index: 'LAST', align: 'end', behavior: 'smooth' });
  };

  return (
    <div className="relative min-h-0 flex-1">
      <Virtuoso
        // Nouvelle conversation : la liste repart du bas
        key={conversationId ?? 'new'}
        ref={virtuoso}
        className="h-full"
        data={items}
        computeItemKey={itemKey}
        initialTopMostItemIndex={{ index: 'LAST', align: 'end' }}
        followOutput={(bottom) => (bottom ? 'auto' : false)}
        atBottomStateChange={onBottom}
        atBottomThreshold={BOTTOM_THRESHOLD}
        totalListHeightChanged={onHeightChange}
        increaseViewportBy={{ top: 800, bottom: 400 }}
        components={{ Header: ThreadHeader, Footer: ThreadFooter }}
        itemContent={(index, item) => (
          <div className="mx-auto w-full max-w-[var(--chat-column)] px-6">
            {item.kind === 'live' ? (
              <AssistantMessage live={item.live} pending={!item.live} isLast />
            ) : item.message.role === 'user' ? (
              <UserMessage message={item.message} branch={branches[item.message.mid]} busy={busy} />
            ) : (
              <AssistantMessage message={item.message} isLast={index === lastIndex} />
            )}
          </div>
        )}
      />
      {!atBottom ? (
        <button
          type="button"
          onClick={scrollToBottom}
          aria-label="Revenir en bas"
          className="absolute bottom-3 left-1/2 flex h-9 w-9 -translate-x-1/2 items-center justify-center rounded-full border border-line bg-bg-2 text-fg-2 shadow-md transition-colors hover:bg-bg-3 hover:text-fg"
          style={{ animation: 'fade-in var(--motion) var(--motion-ease)' }}
        >
          <ArrowDown size={17} />
        </button>
      ) : null}
    </div>
  );
}

function ThreadHeader() {
  return <div className="h-4" />;
}

function ThreadFooter() {
  return <div className="h-6" />;
}
