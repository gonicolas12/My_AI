/*
 * Fil de la conversation Code : liste virtualisée, colonne de lecture centrée,
 * collée en bas pendant une réponse sauf si l'utilisateur est remonté (le
 * bouton « ↓ » l'y ramène), comme le fil du chat. Un message envoyé d'ici
 * ramène en bas ; un message de VS Code ou du téléphone ne déplace pas un
 * lecteur remonté.
 */

import { ArrowDown } from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';
import { Virtuoso, type VirtuosoHandle } from 'react-virtuoso';

import { useT } from '../../i18n';
import type { CodeMessage } from '../../lib/events';
import { useCode } from '../../stores/code';
import { CodeReply, CodeUserBubble } from './CodeTurn';

/** Hauteur sous laquelle on considère être en bas (px) */
const BOTTOM_THRESHOLD = 96;

function itemKey(_index: number, message: CodeMessage): string {
  return `${message.role}:${message.message_id}`;
}

function Top() {
  return <div className="h-4" />;
}

function Bottom() {
  return <div className="h-6" />;
}

export function CodeThread() {
  const t = useT();
  const messages = useCode((state) => state.messages);
  const follow = useCode((state) => state.follow);
  const virtuoso = useRef<VirtuosoHandle>(null);
  const [atBottom, setAtBottom] = useState(true);
  const stick = useRef(true);
  const lastIndex = messages.length - 1;

  const onBottom = useCallback((bottom: boolean) => {
    stick.current = bottom;
    setAtBottom(bottom);
  }, []);

  // La réponse en cours grandit sans ajouter d'élément : rester en bas
  const onHeightChange = useCallback(() => {
    if (stick.current) virtuoso.current?.scrollToIndex({ index: 'LAST', align: 'end' });
  }, []);

  // Message envoyé d'ici : retour en bas, et suivi de la réponse à venir
  const seen = useRef(follow);
  useEffect(() => {
    if (follow === seen.current) return;
    seen.current = follow;
    stick.current = true;
    virtuoso.current?.scrollToIndex({ index: 'LAST', align: 'end' });
  }, [follow]);

  return (
    <div className="relative min-h-0 flex-1">
      <Virtuoso
        ref={virtuoso}
        className="h-full"
        data={messages}
        computeItemKey={itemKey}
        initialTopMostItemIndex={{ index: 'LAST', align: 'end' }}
        followOutput={(bottom) => (bottom ? 'auto' : false)}
        atBottomStateChange={onBottom}
        atBottomThreshold={BOTTOM_THRESHOLD}
        totalListHeightChanged={onHeightChange}
        increaseViewportBy={{ top: 800, bottom: 400 }}
        components={{ Header: Top, Footer: Bottom }}
        itemContent={(index, message) => (
          <div className="mx-auto w-full max-w-[var(--chat-column)] px-6">
            {message.role === 'user' ? (
              <CodeUserBubble message={message} />
            ) : (
              <CodeReply message={message} isLast={index === lastIndex} />
            )}
          </div>
        )}
      />
      {!atBottom ? (
        <button
          type="button"
          onClick={() => {
            stick.current = true;
            virtuoso.current?.scrollToIndex({ index: 'LAST', align: 'end', behavior: 'smooth' });
          }}
          aria-label={t('chat.scrollToBottom')}
          className="absolute bottom-3 left-1/2 flex h-9 w-9 -translate-x-1/2 items-center justify-center rounded-full border border-line bg-bg-2 text-fg-2 shadow-md transition-colors hover:bg-bg-3 hover:text-fg"
          style={{ animation: 'fade-in var(--motion) var(--motion-ease)' }}
        >
          <ArrowDown size={17} />
        </button>
      ) : null}
    </div>
  );
}
