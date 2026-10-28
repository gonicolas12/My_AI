/*
 * Zone de saisie de la page Code : celle du chat (pièces jointes en vignettes,
 * menu « + », Ctrl+V pour coller une image, micro de la dictée locale), avec
 * le dossier ouvert dans VS Code en pied de carte. Les pièces jointes partent
 * avec le message : le modèle lit les documents et le code, le modèle vision
 * décrit les images. Entrée envoie, Maj+Entrée va à la ligne ; pendant une
 * réponse, d'où que vienne son message, le bouton devient Stop.
 */

import { ArrowUp, CodeXml, Square } from 'lucide-react';
import { useEffect, useRef } from 'react';

import { IconButton } from '../../components/ui/Button';
import { t as translate, useT } from '../../i18n';
import { cn } from '../../lib/cn';
import { shell } from '../../lib/shell';
import { notify } from '../../stores/app';
import {
  addCodePaths,
  removeCodeAttachment,
  sendCode,
  setCodeDraft,
  stopCode,
  uploadCodeFiles,
  useCode,
} from '../../stores/code';
import { CLIPBOARD_IMAGE, clipboardFiles } from '../chat/attach';
import { PathChips } from '../chat/AttachmentChips';
import { AttachMenu } from '../chat/AttachMenu';
import { MicButton } from '../chat/MessageControls';

/** Nom que Chromium donne à une image du presse-papiers (capture d'écran) */
const CHROMIUM_CLIPBOARD_NAME = 'image.png';

/** Dossier choisi : ses fichiers lisibles deviennent des pièces jointes, comme s'il était déposé */
async function attachFolder(): Promise<void> {
  if (!shell.canPickFiles()) {
    notify('info', translate('sidebar.folders.pickInWindow'));
    return;
  }
  const path = await shell.pickFolder();
  if (path) await addCodePaths([path]);
}

export function CodeComposer({ variant }: { variant: 'home' | 'dock' }) {
  const t = useT();
  const draft = useCode((state) => state.draft);
  const attachments = useCode((state) => state.attachments);
  const dropping = useCode((state) => state.dropping);
  const sending = useCode((state) => state.sending);
  const busy = useCode((state) => state.state.busy);
  const vscode = useCode((state) => state.state.vscode);
  const workspace = useCode((state) => state.state.workspace);
  const textarea = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    textarea.current?.focus();
  }, []);

  const hasContent = draft.trim().length > 0 || attachments.length > 0;
  const canSend = hasContent && vscode && !busy && !sending;

  const submit = async () => {
    const text = draft.trim();
    if (!canSend) return;
    if (await sendCode(text)) setCodeDraft('');
    textarea.current?.focus();
  };

  /** Texte dicté : inséré au curseur, une espace devant s'il colle au mot précédent (Tk) */
  const insertDictation = (spoken: string) => {
    const element = textarea.current;
    const current = useCode.getState().draft;
    const at = element ? element.selectionStart : current.length;
    const before = current.slice(0, at);
    const inserted = (before && !/\s$/.test(before) ? ' ' : '') + spoken;
    setCodeDraft(before + inserted + current.slice(at));
    requestAnimationFrame(() => {
      if (!element) return;
      element.focus();
      const caret = before.length + inserted.length;
      element.setSelectionRange(caret, caret);
    });
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
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
      void uploadCodeFiles([file], name);
    }
  };

  return (
    <div className={cn('w-full', variant === 'dock' && 'px-6 pb-5')}>
      <div className="mx-auto w-full max-w-[var(--chat-column)]">
        <div
          className={cn(
            'relative rounded-xl border bg-bg-2 shadow-md transition-colors duration-150',
            dropping ? 'border-accent' : 'border-line focus-within:border-line-2',
          )}
        >
          <PathChips items={attachments} onRemove={removeCodeAttachment} />
          <textarea
            ref={textarea}
            value={draft}
            onChange={(event) => setCodeDraft(event.target.value)}
            onKeyDown={onKeyDown}
            onPaste={onPaste}
            placeholder={vscode ? t('code.placeholder') : t('code.placeholderOffline')}
            rows={1}
            aria-label={t('code.inputLabel')}
            className={cn(
              'block max-h-[280px] w-full resize-none overflow-y-auto bg-transparent px-4 pt-3.5 text-chat leading-relaxed text-fg outline-none [field-sizing:content] placeholder:text-fg-3',
              variant === 'home' ? 'min-h-24' : 'min-h-12',
            )}
          />
          <div className="flex items-center gap-1 px-2.5 pt-1 pb-2.5">
            <AttachMenu
              onAttachFolder={() => void attachFolder()}
              onPaths={(paths) => void addCodePaths(paths)}
              onFiles={(files) => void uploadCodeFiles(files)}
            />
            {vscode && workspace ? (
              <span
                className="inline-flex max-w-[55%] items-center gap-1.5 rounded-md px-1.5 py-1 font-mono text-xs text-fg-2"
                title={t('code.workspace', { name: workspace })}
              >
                <CodeXml size={14} className="shrink-0 text-accent" />
                <span className="truncate">{workspace}</span>
              </span>
            ) : null}
            <div className="flex-1" />
            <MicButton onTranscript={insertDictation} />
            {busy ? (
              <IconButton
                label={t('code.stop')}
                shortcut="Escape"
                tooltipSide="top"
                onClick={() => void stopCode()}
                className="h-8 w-8 rounded-full bg-fg text-bg hover:bg-fg-2 hover:text-bg"
              >
                <Square size={12} fill="currentColor" />
              </IconButton>
            ) : (
              <IconButton
                label={t('code.send')}
                shortcut="Enter"
                tooltipSide="top"
                disabled={!canSend}
                onClick={() => void submit()}
                className={cn(
                  'h-8 w-8 rounded-full',
                  canSend
                    ? 'bg-accent text-on-accent hover:bg-accent-hover hover:text-on-accent'
                    : 'bg-bg-3 text-fg-3',
                )}
              >
                <ArrowUp size={17} strokeWidth={2.4} />
              </IconButton>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
