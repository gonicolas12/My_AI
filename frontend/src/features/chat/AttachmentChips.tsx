/*
 * Pièces jointes de la zone de saisie, en vignettes au-dessus du texte : une
 * miniature pour une image, une icône sinon ; un cercle tourne tant que le
 * serveur lit le fichier, et l'envoi attend la fin de la lecture. Retirer une
 * pièce jointe arrête sa lecture (comme add_file_preview dans Tk).
 */

import { LoaderCircle, X } from 'lucide-react';
import { createElement } from 'react';

import { type MessageKey, useT } from '../../i18n';
import { api } from '../../lib/api';
import type { AttachmentView } from '../../lib/events';
import { cn } from '../../lib/cn';
import { useFileUrl } from '../../lib/files';
import { useChat } from '../../stores/chat';
import { attachmentIcon } from './attachKinds';

const STATUS_LABEL: Record<AttachmentView['status'], MessageKey> = {
  loading: 'chat.attachment.status.loading',
  ready: 'chat.attachment.status.ready',
  error: 'chat.attachment.status.error',
};

function Chip({ attachment }: { attachment: AttachmentView }) {
  const t = useT();
  const image = attachment.type === 'Image';
  const url = useFileUrl(image ? attachment.path : null);
  const loading = attachment.status === 'loading';
  return (
    <span
      title={t('chat.attachment.title', {
        path: attachment.path,
        status: t(STATUS_LABEL[attachment.status]),
      })}
      className={cn(
        'inline-flex h-9 max-w-60 items-center gap-2 rounded-md border bg-bg-3 px-1 text-xs',
        attachment.status === 'error' ? 'border-error/60 text-error' : 'border-line text-fg-2',
      )}
    >
      <span className="relative flex h-7 w-7 shrink-0 items-center justify-center overflow-hidden rounded-xs bg-bg-2">
        {image && url ? (
          <img src={url} alt="" className="h-full w-full object-cover" draggable={false} />
        ) : (
          createElement(attachmentIcon(attachment.type), { size: 15 })
        )}
        {loading ? (
          <span className="absolute inset-0 flex items-center justify-center bg-bg-2/70">
            <LoaderCircle
              size={15}
              className="spin text-accent"
              aria-label={t('chat.attachment.reading')}
            />
          </span>
        ) : null}
      </span>
      <span className="truncate">{attachment.name}</span>
      <button
        type="button"
        aria-label={t('chat.attachment.remove', { name: attachment.name })}
        onClick={() => void api.removeAttachment(attachment.id).catch(() => undefined)}
        className="shrink-0 rounded-xs p-1 text-fg-3 hover:bg-hover hover:text-fg"
      >
        <X size={12} />
      </button>
    </span>
  );
}

export function AttachmentChips() {
  const attachments = useChat((state) => state.attachments);
  if (!attachments.length) return null;
  return (
    <div className="flex flex-wrap gap-1.5 px-3 pt-3">
      {attachments.map((attachment) => (
        <Chip key={attachment.id} attachment={attachment} />
      ))}
    </div>
  );
}
