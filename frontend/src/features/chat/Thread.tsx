/*
 * Fil de messages : liste virtualisée (react-virtuoso), colonne de lecture
 * centrée. Le défilement reste collé en bas pendant une réponse, sauf si
 * l'utilisateur est remonté : le bouton « ↓ » le ramène alors en bas. Un
 * message envoyé d'ici (ou modifié, ou régénéré) ramène aussi en bas, comme
 * dans Tk ; un message du téléphone ne déplace pas un lecteur remonté.
 */

import { ArrowDown } from 'lucide-react';
import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Virtuoso, type VirtuosoHandle } from 'react-virtuoso';

import type { MessageView } from '../../lib/events';
import { clearHighlight, findResultMessage, highlightElement } from '../../lib/highlight';
import { useChat, useFollow } from '../../stores/chat';
import { clearHighlightTarget, type HighlightTarget, useHighlight } from '../../stores/highlight';
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

/** Question d'une réponse : le message de l'utilisateur qui la précède */
function questionOf(messages: MessageView[], index: number): string | undefined {
  const previous = messages[index - 1];
  return previous?.role === 'user' ? previous.mid : undefined;
}

/** Des messages suivent le tour (question et réponse) qui commence à `index` */
function followsTurn(messages: MessageView[], index: number): boolean {
  const answered = messages[index + 1]?.role === 'assistant';
  return index + (answered ? 2 : 1) < messages.length;
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

  // Résultat de la recherche globale : défiler jusqu'au message, puis le surligner
  const target = useHighlight((state) => state.target);
  const handled = useRef<HighlightTarget | null>(null);
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);
  useEffect(() => {
    if (!target || handled.current === target) return;
    if (target.conversationId !== conversationId || !messages.length) return;
    handled.current = target;
    clearHighlightTarget();
    const index = findResultMessage(messages, target.excerpt, target.messageIndex);
    const mid = messages[index]?.mid;
    if (!mid) return;
    stick.current = false;
    if (poll.current) clearInterval(poll.current);
    let tries = 0;
    // Liste virtualisée : le message n'existe dans la page qu'une fois affiché.
    // La liste d'une conversation qui vient de s'ouvrir se place d'abord en
    // bas : le défilement est redemandé tant que le message n'est pas là.
    poll.current = setInterval(() => {
      const element = document.querySelector<HTMLElement>(`[data-mid="${CSS.escape(mid)}"]`);
      tries += 1;
      if (!element && tries < 40) {
        if (tries % 3 === 1) virtuoso.current?.scrollToIndex({ index, align: 'center' });
        return;
      }
      if (poll.current) clearInterval(poll.current);
      poll.current = null;
      if (element) highlightElement(element, target.query);
    }, 50);
  }, [target, conversationId, messages]);
  useEffect(
    () => () => {
      if (poll.current) clearInterval(poll.current);
      clearHighlight();
    },
    [conversationId],
  );

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

  // Nouveau tour parti d'ici : retour en bas, et suivi de la réponse à venir
  const followRequests = useFollow((state) => state.requests);
  const seenRequests = useRef(followRequests);
  useEffect(() => {
    if (followRequests === seenRequests.current) return;
    seenRequests.current = followRequests;
    stick.current = true;
    virtuoso.current?.scrollToIndex({ index: 'LAST', align: 'end' });
  }, [followRequests]);

  return (
    // Comme une sélection à la souris : le surlignage disparaît au clic
    <div className="relative min-h-0 flex-1" onMouseDown={clearHighlight}>
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
          <div
            className="mx-auto w-full max-w-[var(--chat-column)] px-6"
            data-mid={item.kind === 'message' ? item.message.mid : undefined}
          >
            {item.kind === 'live' ? (
              <AssistantMessage live={item.live} pending={!item.live} isLast />
            ) : item.message.role === 'user' ? (
              <UserMessage
                message={item.message}
                branch={branches[item.message.mid]}
                busy={busy}
                hasFollowing={followsTurn(messages, index)}
              />
            ) : (
              <AssistantMessage
                message={item.message}
                isLast={index === lastIndex}
                userMid={questionOf(messages, index)}
                hasFollowing={index < messages.length - 1}
                busy={busy}
              />
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
