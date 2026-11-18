/*
 * Pièces jointes de la zone de saisie, en vignettes au-dessus du texte : une
 * miniature pour une image, une icône sinon ; un cercle tourne tant que le
 * serveur lit le fichier, et l'envoi attend la fin de la lecture. Retirer une
 * pièce jointe arrête sa lecture (comme add_file_preview dans Tk).
 *
 * PathChips : celles qu'une page garde elle-même, par leur chemin (zone de
 * tâche des agents, page Code), lues au moment de l'envoi.
 *
 * Un clic sur l'une (pas encore envoyée) ouvre sa fenêtre d'aperçu, au premier
 * plan ; celles d'un message envoyé s'ouvrent dans le volet de droite.
 */

import { LoaderCircle, X } from 'lucide-react';
import { createElement, type ReactNode } from 'react';

import { type MessageKey, useT } from '../../i18n';
import { api } from '../../lib/api';
import type { AttachmentView } from '../../lib/events';
import { cn } from '../../lib/cn';
import { useFileUrl } from '../../lib/files';
import { openAttachmentPreview, type PreviewFile } from '../../stores/attachmentPreview';
import { useChat } from '../../stores/chat';
import { attachmentIcon } from './attachKinds';

const STATUS_LABEL: Record<AttachmentView['status'], MessageKey> = {
  loading: 'chat.attachment.status.loading',
  ready: 'chat.attachment.status.ready',
  error: 'chat.attachment.status.error',
};

/** Vignette et nom d'une pièce jointe : un clic ouvre sa fenêtre d'aperçu */
function ChipOpen({
  name,
  title,
  onOpen,
  children,
}: {
  name: string;
  title: string;
  onOpen: () => void;
  children: ReactNode;
}) {
  const t = useT();
  return (
    <button
      type="button"
      onClick={onOpen}
      title={title}
      aria-label={t('chat.file.preview', { name })}
      className="group flex min-w-0 items-center gap-2 rounded-xs text-start"
    >
      {children}
      <span className="truncate underline decoration-transparent underline-offset-2 transition-colors duration-150 group-hover:text-link group-hover:decoration-link/60">
        {name}
      </span>
    </button>
  );
}

function Chip({ attachment, onOpen }: { attachment: AttachmentView; onOpen: () => void }) {
  const t = useT();
  const image = attachment.type === 'Image';
  const url = useFileUrl(image ? attachment.path : null);
  const loading = attachment.status === 'loading';
  return (
    <span
      className={cn(
        'inline-flex h-9 max-w-60 items-center gap-2 rounded-md border bg-bg-3 px-1 text-xs',
        attachment.status === 'error' ? 'border-error/60 text-error' : 'border-line text-fg-2',
      )}
    >
      <ChipOpen
        name={attachment.name}
        title={t('chat.attachment.title', {
          path: attachment.path,
          status: t(STATUS_LABEL[attachment.status]),
        })}
        onOpen={onOpen}
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
      </ChipOpen>
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

interface PathItem {
  id: string;
  path: string;
  name: string;
  type: string;
}

function PathChip({
  item,
  onRemove,
  onOpen,
}: {
  item: PathItem;
  onRemove: (id: string) => void;
  onOpen: () => void;
}) {
  const t = useT();
  const image = item.type === 'Image';
  const url = useFileUrl(image ? item.path : null);
  return (
    <span className="inline-flex h-9 max-w-60 items-center gap-2 rounded-md border border-line bg-bg-3 px-1 text-xs text-fg-2">
      <ChipOpen name={item.name} title={item.path} onOpen={onOpen}>
        <span className="flex h-7 w-7 shrink-0 items-center justify-center overflow-hidden rounded-xs bg-bg-2">
          {image && url ? (
            <img src={url} alt="" className="h-full w-full object-cover" draggable={false} />
          ) : (
            createElement(attachmentIcon(item.type), { size: 15 })
          )}
        </span>
      </ChipOpen>
      <button
        type="button"
        aria-label={t('chat.attachment.remove', { name: item.name })}
        onClick={() => onRemove(item.id)}
        className="shrink-0 rounded-xs p-1 text-fg-3 hover:bg-hover hover:text-fg"
      >
        <X size={12} />
      </button>
    </span>
  );
}

export function PathChips({
  items,
  onRemove,
}: {
  items: PathItem[];
  onRemove: (id: string) => void;
}) {
  if (!items.length) return null;
  const files: PreviewFile[] = items.map(({ path, name }) => ({ path, name }));
  return (
    <div className="flex flex-wrap gap-1.5 px-3 pt-3">
      {items.map((item, index) => (
        <PathChip
          key={item.id}
          item={item}
          onRemove={onRemove}
          onOpen={() => openAttachmentPreview(files, index)}
        />
      ))}
    </div>
  );
}

export function AttachmentChips() {
  const attachments = useChat((state) => state.attachments);
  if (!attachments.length) return null;
  const files: PreviewFile[] = attachments.map(({ path, name }) => ({ path, name }));
  return (
    <div className="flex flex-wrap gap-1.5 px-3 pt-3">
      {attachments.map((attachment, index) => (
        <Chip
          key={attachment.id}
          attachment={attachment}
          onOpen={() => openAttachmentPreview(files, index)}
        />
      ))}
    </div>
  );
}
