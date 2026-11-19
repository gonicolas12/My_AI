import { ChevronLeft, ChevronRight, Smartphone } from 'lucide-react';
import { memo, useState } from 'react';

import { IconButton } from '../../components/ui/Button';
import { useT } from '../../i18n';
import { api } from '../../lib/api';
import { fileArtifact } from '../../lib/artifacts';
import type { MessageView } from '../../lib/events';
import { formatTime } from '../../lib/format';
import { notify } from '../../stores/app';
import { openPreview } from '../../stores/preview';
import { splitAttachmentLines } from './attachments';
import { EditDialog } from './EditDialog';
import { CopyButton, MessageActions } from './MessageActions';
import { EditButton } from './MessageControls';
import { SentAttachment } from './SentAttachment';

interface UserMessageProps {
  message: MessageView;
  /** Variantes d'édition de ce tour (‹ k/n ›) */
  branch?: { count: number; current: number } | undefined;
  /** Réponse en cours : ni changement de variante ni modification */
  busy: boolean;
  /** Des messages suivent la réponse de ce tour */
  hasFollowing?: boolean;
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
          {attachments.map((att, index) => (
            <SentAttachment
              key={att.path}
              attachment={att}
              onOpen={() =>
                openPreview(
                  message.mid,
                  attachments.map((item, at) => fileArtifact(item.path, false, at)),
                  index,
                )
              }
            />
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
