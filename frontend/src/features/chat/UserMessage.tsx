import { ChevronLeft, ChevronRight, Smartphone } from 'lucide-react';
import { createElement, memo, useState } from 'react';

import { IconButton } from '../../components/ui/Button';
import { Lightbox } from '../../components/ui/Lightbox';
import { useT } from '../../i18n';
import { revealPath } from '../../lib/actions';
import { api } from '../../lib/api';
import { documentArtifacts } from '../../lib/artifacts';
import type { AttachmentRef, MessageView } from '../../lib/events';
import { useFileUrl } from '../../lib/files';
import { formatTime } from '../../lib/format';
import { notify } from '../../stores/app';
import { openPreview } from '../../stores/preview';
import { attachmentIcon } from './attachKinds';
import { splitAttachmentLines } from './attachments';
import { EditDialog } from './EditDialog';
import { CopyButton, MessageActions } from './MessageActions';
import { EditButton } from './MessageControls';

interface UserMessageProps {
  message: MessageView;
  /** Variantes d'édition de ce tour (‹ k/n ›) */
  branch?: { count: number; current: number } | undefined;
  /** Réponse en cours : ni changement de variante ni modification */
  busy: boolean;
  /** Des messages suivent la réponse de ce tour */
  hasFollowing?: boolean;
}

/**
 * Pièce jointe d'un message envoyé : une image s'agrandit, un document qui a
 * un aperçu s'ouvre dans le volet, un autre fichier se montre dans l'Explorateur.
 */
function SentAttachment({ attachment, mid }: { attachment: AttachmentRef; mid: string }) {
  const image = attachment.type === 'Image';
  const url = useFileUrl(image ? attachment.path : null);
  const [zoom, setZoom] = useState(false);
  const open = () => {
    if (image) {
      setZoom(true);
      return;
    }
    const [artifact] = documentArtifacts([attachment.path], 0, false);
    if (artifact) openPreview(mid, [artifact]);
    else void revealPath(attachment.path);
  };
  return (
    <>
      <button
        type="button"
        onClick={open}
        title={attachment.path}
        className="inline-flex h-9 max-w-64 items-center gap-2 rounded-md border border-line bg-bg-2 ps-1 pe-2.5 text-xs text-fg-2 transition-colors duration-150 hover:border-line-2 hover:text-fg"
      >
        <span className="flex h-7 w-7 shrink-0 items-center justify-center overflow-hidden rounded-xs bg-bg-3">
          {image && url ? (
            <img src={url} alt="" className="h-full w-full object-cover" draggable={false} />
          ) : (
            createElement(attachmentIcon(attachment.type), { size: 14 })
          )}
        </span>
        <span className="truncate">{attachment.name}</span>
      </button>
      {image ? (
        <Lightbox
          open={zoom}
          onOpenChange={setZoom}
          url={url}
          path={attachment.path}
          name={attachment.name}
          generated={false}
        />
      ) : null}
    </>
  );
}

function navigate(mid: string, version: number) {
  api.navigate(mid, version).catch((error: unknown) => {
    notify('warning', error instanceof Error ? error.message : String(error));
  });
}

export const UserMessage = memo(function UserMessage({
  message,
  branch,
  busy,
  hasFollowing = false,
}: UserMessageProps) {
  const t = useT();
  const { body } = splitAttachmentLines(message.text);
  const attachments = message.attachments;
  const [editing, setEditing] = useState(false);

  return (
    <div className="group/msg flex flex-col items-end py-3">
      {message.source === 'mobile' ? (
        <span className="mb-1.5 inline-flex items-center gap-1 rounded-full border border-line px-2 py-0.5 text-2xs font-medium text-fg-2">
          <Smartphone size={11} />
          {t('chat.queue.mobile')}
        </span>
      ) : null}
      {body ? (
        <div className="max-w-[85%] rounded-xl rounded-ee-sm bg-user px-4 py-2.5 text-chat leading-relaxed break-words whitespace-pre-wrap text-on-user">
          {body}
        </div>
      ) : null}
      {attachments.length ? (
        <div className="mt-1.5 flex max-w-[85%] flex-wrap justify-end gap-1.5">
          {attachments.map((att) => (
            <SentAttachment key={att.path} attachment={att} mid={message.mid} />
          ))}
        </div>
      ) : null}
      <MessageActions align="end" meta={formatTime(message.timestamp)}>
        <CopyButton text={body} label={t('chat.message.copyUser')} />
        {body ? <EditButton busy={busy} onClick={() => setEditing(true)} /> : null}
        {branch && branch.count > 1 ? (
          <div className="flex items-center text-xs text-fg-2 tabular-nums">
            <IconButton
              label={t('chat.message.previousVersion')}
              size="sm"
              disabled={busy || branch.current <= 0}
              onClick={() => navigate(message.mid, branch.current - 1)}
            >
              <ChevronLeft size={15} className="rtl:-scale-x-100" />
            </IconButton>
            <span className="px-0.5">
              {branch.current + 1}/{branch.count}
            </span>
            <IconButton
              label={t('chat.message.nextVersion')}
              size="sm"
              disabled={busy || branch.current >= branch.count - 1}
              onClick={() => navigate(message.mid, branch.current + 1)}
            >
              <ChevronRight size={15} className="rtl:-scale-x-100" />
            </IconButton>
          </div>
        ) : null}
      </MessageActions>
      {editing ? (
        <EditDialog
          message={message}
          hasFollowing={hasFollowing}
          onClose={() => setEditing(false)}
        />
      ) : null}
    </div>
  );
});
