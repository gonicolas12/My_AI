/*
 * Zone de saisie en forme de carte : pièces jointes en vignettes au-dessus du
 * texte, menu « + », micro, bouton d'envoi rond qui devient un carré Stop
 * pendant la génération.
 *
 * Entrée envoie, Maj+Entrée va à la ligne. Pendant une réponse, un message
 * envoyé attend son tour dans la file commune au desktop et au mobile (D1).
 * « / » en début de saisie propose les slash commands (↑/↓, Entrée ou Tab,
 * Échap) ; Ctrl+V colle une image comme pièce jointe.
 */

import { ArrowUp, Mic, Square } from 'lucide-react';
import { useEffect, useId, useRef, useState } from 'react';

import { IconButton } from '../../components/ui/Button';
import { Tooltip } from '../../components/ui/Tooltip';
import { sendMessage, stopGeneration } from '../../lib/actions';
import type { SlashCommand } from '../../lib/api';
import { cn } from '../../lib/cn';
import { useApp } from '../../stores/app';
import { useChat } from '../../stores/chat';
import { isGenerating } from '../../stores/chatReducer';
import { setDraft, useComposer } from '../../stores/composer';
import { CLIPBOARD_IMAGE, clipboardFiles, uploadFiles } from './attach';
import { AttachmentChips } from './AttachmentChips';
import { AttachMenu } from './AttachMenu';
import { QueueList } from './QueueList';
import { commandText, useSlashCommands } from './slash';
import { SlashMenu } from './SlashMenu';

const PLACEHOLDER = 'Tapez votre message...';

/** Nom que Chromium donne à une image du presse-papiers (capture d'écran) */
const CHROMIUM_CLIPBOARD_NAME = 'image.png';

interface ComposerProps {
  /** Accueil : carte plus haute, au centre de la page */
  variant: 'home' | 'dock';
}

export function Composer({ variant }: ComposerProps) {
  const draft = useComposer((state) => state.draft);
  const dropping = useComposer((state) => state.dropping);
  const generating = useChat(isGenerating);
  const ready = useApp((state) => state.status?.state === 'ready');
  const textarea = useRef<HTMLTextAreaElement>(null);
  const [sending, setSending] = useState(false);
  const listId = useId();

  // Slash commands : la liste se ferme avec Échap ou quand la saisie perd le focus
  const commands = useSlashCommands(draft);
  const [focused, setFocused] = useState(true);
  const [dismissed, setDismissed] = useState<string | null>(null);
  const [active, setActive] = useState(0);
  const slashOpen = focused && commands.length > 0 && dismissed !== draft;
  const activeIndex = Math.min(active, commands.length - 1);

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

  const choose = (command: SlashCommand) => {
    const text = commandText(command);
    setDraft(text);
    setDismissed(text);
    // Curseur en fin de ligne, prêt pour les arguments
    requestAnimationFrame(() => {
      const element = textarea.current;
      if (!element) return;
      element.focus();
      element.setSelectionRange(text.length, text.length);
    });
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (slashOpen) {
      if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
        event.preventDefault();
        const step = event.key === 'ArrowDown' ? 1 : -1;
        setActive((activeIndex + step + commands.length) % commands.length);
        return;
      }
      if ((event.key === 'Enter' && !event.shiftKey) || event.key === 'Tab') {
        event.preventDefault();
        const command = commands[activeIndex];
        if (command) choose(command);
        return;
      }
      if (event.key === 'Escape') {
        event.preventDefault();
        setDismissed(draft);
        return;
      }
    }
    if (event.key === 'Enter' && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void submit();
    }
  };

  const onPaste = (event: React.ClipboardEvent<HTMLTextAreaElement>) => {
    const files = clipboardFiles(event);
    // Du texte copié (même depuis Word, qui y joint une image) se colle comme du texte
    if (!files.length || event.clipboardData.getData('text/plain').trim()) return;
    event.preventDefault();
    for (const file of files) {
      const name = file.name === CHROMIUM_CLIPBOARD_NAME ? CLIPBOARD_IMAGE : file.name;
      void uploadFiles([file], name);
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
            'relative rounded-xl border bg-bg-2 shadow-md transition-colors duration-150',
            dropping ? 'border-accent' : 'border-line focus-within:border-line-2',
          )}
        >
          {slashOpen ? (
            <SlashMenu
              id={listId}
              commands={commands}
              active={activeIndex}
              onHover={setActive}
              onChoose={choose}
            />
          ) : null}
          <AttachmentChips />
          <textarea
            ref={textarea}
            value={draft}
            onChange={(event) => {
              setDraft(event.target.value);
              setActive(0);
            }}
            onKeyDown={onKeyDown}
            onPaste={onPaste}
            onFocus={() => setFocused(true)}
            onBlur={() => setFocused(false)}
            placeholder={PLACEHOLDER}
            rows={1}
            aria-label="Message"
            aria-controls={slashOpen ? listId : undefined}
            aria-autocomplete="list"
            aria-activedescendant={slashOpen ? `${listId}-${activeIndex}` : undefined}
            className={cn(
              // Hauteur suivant le texte (field-sizing), sans mesure en JavaScript
              'block max-h-[280px] w-full resize-none overflow-y-auto bg-transparent px-4 pt-3.5 text-chat leading-relaxed text-fg outline-none [field-sizing:content] placeholder:text-fg-3',
              variant === 'home' ? 'min-h-24' : 'min-h-12',
            )}
          />
          <div className="flex items-center gap-1 px-2.5 pt-1 pb-2.5">
            <AttachMenu />
            <div className="flex-1" />
            <Tooltip label="Saisie vocale : arrive avec la suite de la phase 3" side="top">
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
