/*
 * Modifier un message envoyé puis régénérer la réponse (_begin_edit et
 * _apply_edit de message_editing.py) : l'ancienne version reste accessible
 * par ‹ k/n ›, pièces jointes conservées. Ctrl+Entrée valide, Échap annule ;
 * un texte inchangé ne fait rien.
 */

import { RotateCcw } from 'lucide-react';
import { useState } from 'react';

import { Button } from '../../components/ui/Button';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { Dialog } from '../../components/ui/Dialog';
import { useT } from '../../i18n';
import { editMessage } from '../../lib/actions';
import type { MessageView } from '../../lib/events';
import { splitAttachmentLines } from './attachments';

interface EditDialogProps {
  message: MessageView;
  /** Des messages suivent ce tour : ils laisseront place à la nouvelle réponse */
  hasFollowing: boolean;
  onClose: () => void;
}

export function EditDialog({ message, hasFollowing, onClose }: EditDialogProps) {
  const t = useT();
  const { body } = splitAttachmentLines(message.text);
  const [text, setText] = useState(body);
  const [confirming, setConfirming] = useState(false);
  const names = message.attachments.map((attachment) => attachment.name);

  const apply = () => {
    onClose();
    void editMessage(message.mid, text.trim());
  };
  const submit = () => {
    const trimmed = text.trim();
    if (!trimmed || trimmed === body.trim()) {
      onClose();
      return;
    }
    if (hasFollowing) setConfirming(true);
    else apply();
  };

  return (
    <>
      <Dialog
        open={!confirming}
        onOpenChange={(open) => {
          if (!open) onClose();
        }}
        title={t('chat.edit.title')}
        description={t('chat.edit.description')}
        width={560}
        footer={
          <>
            <Button variant="secondary" onClick={onClose}>
              {t('common.cancel')}
            </Button>
            <Button variant="primary" onClick={submit}>
              <RotateCcw size={15} />
              {t('chat.edit.regenerate')}
            </Button>
          </>
        }
      >
        <textarea
          value={text}
          onChange={(event) => setText(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
              event.preventDefault();
              submit();
            }
          }}
          aria-label={t('chat.edit.textLabel')}
          autoFocus
          rows={6}
          className="block max-h-[50vh] w-full resize-y rounded-md border border-line bg-bg px-3 py-2.5 text-chat leading-relaxed text-fg outline-none focus:border-line-2"
        />
        {names.length ? (
          <p className="mt-2 text-xs text-fg-2">
            {t('chat.edit.keptAttachments', { names: names.join(', ') })}
          </p>
        ) : null}
      </Dialog>
      <ConfirmDialog
        open={confirming}
        onOpenChange={(open) => {
          if (!open) onClose();
        }}
        title={t('chat.edit.title')}
        message={t('chat.branchWarning')}
        confirmLabel={t('common.continue')}
        onConfirm={apply}
      />
    </>
  );
}
