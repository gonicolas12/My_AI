/*
 * Zone de saisie en forme de carte : pièces jointes en puces au-dessus du
 * texte, menu « + », micro, bouton d'envoi rond qui devient un carré Stop
 * pendant la génération.
 *
 * Entrée envoie, Maj+Entrée va à la ligne. Pendant une réponse, un message
 * envoyé attend son tour dans la file commune au desktop et au mobile (D1).
 */

import { ArrowUp, FileText, ImageIcon, LoaderCircle, Mic, Plus, Square, X } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { IconButton } from '../../components/ui/Button';
import { Tooltip } from '../../components/ui/Tooltip';
import { sendMessage, stopGeneration } from '../../lib/actions';
import { api } from '../../lib/api';
import { cn } from '../../lib/cn';
import { useApp } from '../../stores/app';
import { useChat } from '../../stores/chat';
import { isGenerating } from '../../stores/chatReducer';
import { setDraft, useComposer } from '../../stores/composer';
import { QueueList } from './QueueList';

const PLACEHOLDER = 'Tapez votre message...';

function AttachmentChips() {
  const attachments = useChat((state) => state.attachments);
  if (!attachments.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5 px-3 pt-3">
      {attachments.map((att) => (
        <span
          key={att.id}
          title={att.path}
          className={cn(
            'inline-flex max-w-56 items-center gap-1.5 rounded-md border bg-bg-3 py-1 pr-1 pl-2 text-xs',
            att.status === 'error' ? 'border-error/60 text-error' : 'border-line text-fg-2',
          )}
        >
          {att.status === 'loading' ? (
            <LoaderCircle size={13} className="spin shrink-0 text-accent" />
          ) : att.type === 'Image' ? (
            <ImageIcon size={13} className="shrink-0" />
          ) : (
            <FileText size={13} className="shrink-0" />
          )}
          <span className="truncate">{att.name}</span>
          <button
            type="button"
            aria-label={`Retirer ${att.name}`}
            onClick={() => void api.removeAttachment(att.id).catch(() => undefined)}
            className="rounded-xs p-0.5 text-fg-3 hover:bg-hover hover:text-fg"
          >
            <X size={12} />
          </button>
        </span>
      ))}
    </div>
  );
}

interface ComposerProps {
  /** Accueil : carte plus haute, au centre de la page */
  variant: 'home' | 'dock';
}

export function Composer({ variant }: ComposerProps) {
  const draft = useComposer((state) => state.draft);
  const generating = useChat(isGenerating);
  const ready = useApp((state) => state.status?.state === 'ready');
  const textarea = useRef<HTMLTextAreaElement>(null);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    textarea.current?.focus();
  }, []);

  const hasText = draft.trim().length > 0;
  const showStop = generating && !hasText;

  const submit = async () => {
    const text = draft.trim();
    if (!text || sending || !ready) return;
    setSending(true);
    const sent = await sendMessage(text);
    setSending(false);
    if (sent) setDraft('');
    textarea.current?.focus();
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void submit();
    }
  };

  const action = showStop ? (
    <IconButton
      label="Arrêter la réponse"
      shortcut="Échap"
      tooltipSide="top"
      onClick={() => void stopGeneration()}
      className="h-8 w-8 rounded-full bg-fg text-bg hover:bg-fg-2 hover:text-bg"
    >
      <Square size={12} fill="currentColor" />
    </IconButton>
  ) : (
    <IconButton
      label={generating ? 'Mettre en file d’attente' : 'Envoyer'}
      shortcut="Entrée"
      tooltipSide="top"
      disabled={!hasText || sending || !ready}
      onClick={() => void submit()}
      className={cn(
        'h-8 w-8 rounded-full',
        hasText && ready
          ? 'bg-accent text-on-accent hover:bg-accent-hover hover:text-on-accent'
          : 'bg-bg-3 text-fg-3',
      )}
    >
      <ArrowUp size={17} strokeWidth={2.4} />
    </IconButton>
  );

  return (
    <div className={cn('w-full', variant === 'dock' && 'px-6 pb-5')}>
      <div className="mx-auto w-full max-w-[var(--chat-column)]">
        {variant === 'dock' ? <QueueList /> : null}
        <div
          className={cn(
            'rounded-xl border border-line bg-bg-2 shadow-md transition-colors duration-150',
            'focus-within:border-line-2',
          )}
        >
          <AttachmentChips />
          <textarea
            ref={textarea}
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            placeholder={PLACEHOLDER}
            rows={1}
            aria-label="Message"
            className={cn(
              // Hauteur suivant le texte (field-sizing), sans mesure en JavaScript
              'block max-h-[280px] w-full resize-none overflow-y-auto bg-transparent px-4 pt-3.5 text-chat leading-relaxed text-fg outline-none [field-sizing:content] placeholder:text-fg-3',
              variant === 'home' ? 'min-h-24' : 'min-h-12',
            )}
          />
          <div className="flex items-center gap-1 px-2.5 pt-1 pb-2.5">
            <Tooltip label="Joindre un fichier : arrive à la phase 3" side="top">
              <span className="inline-flex">
                <button
                  type="button"
                  disabled
                  aria-label="Joindre un fichier"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-fg-3"
                >
                  <Plus size={18} />
                </button>
              </span>
            </Tooltip>
            <div className="flex-1" />
            <Tooltip label="Saisie vocale : arrive à la phase 3" side="top">
              <span className="inline-flex">
                <button
                  type="button"
                  disabled
                  aria-label="Saisie vocale"
                  className="inline-flex h-8 w-8 items-center justify-center rounded-md text-fg-3"
                >
                  <Mic size={17} />
                </button>
              </span>
            </Tooltip>
            {action}
          </div>
        </div>
      </div>
    </div>
  );
}
