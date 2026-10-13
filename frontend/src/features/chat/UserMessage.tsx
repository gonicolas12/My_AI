import { ChevronLeft, ChevronRight, FileText, ImageIcon, Smartphone } from 'lucide-react';
import { memo } from 'react';

import { IconButton } from '../../components/ui/Button';
import { api } from '../../lib/api';
import type { MessageView } from '../../lib/events';
import { formatTime } from '../../lib/format';
import { notify } from '../../stores/app';
import { splitAttachmentLines } from './attachments';
import { CopyButton, MessageActions } from './MessageActions';

interface UserMessageProps {
  message: MessageView;
  /** Variantes d'édition de ce tour (‹ k/n ›) */
  branch?: { count: number; current: number } | undefined;
  /** Réponse en cours : pas de changement de variante */
  busy: boolean;
}

function navigate(mid: string, version: number) {
  api.navigate(mid, version).catch((error: unknown) => {
    notify('warning', error instanceof Error ? error.message : String(error));
  });
}

export const UserMessage = memo(function UserMessage({ message, branch, busy }: UserMessageProps) {
  const { body } = splitAttachmentLines(message.text);
  const attachments = message.attachments;

  return (
    <div className="group/msg flex flex-col items-end py-3">
      {message.source === 'mobile' ? (
        <span className="mb-1.5 inline-flex items-center gap-1 rounded-full border border-line px-2 py-0.5 text-2xs font-medium text-fg-2">
          <Smartphone size={11} />
          Mobile
        </span>
      ) : null}
      {body ? (
        <div className="max-w-[85%] rounded-xl rounded-br-sm bg-user px-4 py-2.5 text-chat leading-relaxed break-words whitespace-pre-wrap text-on-user">
          {body}
        </div>
      ) : null}
      {attachments.length ? (
        <div className="mt-1.5 flex max-w-[85%] flex-wrap justify-end gap-1.5">
          {attachments.map((att) => (
            <span
              key={att.path}
              title={att.path}
              className="inline-flex max-w-64 items-center gap-1.5 rounded-md border border-line bg-bg-2 px-2 py-1 text-xs text-fg-2"
            >
              {att.type === 'Image' ? <ImageIcon size={13} /> : <FileText size={13} />}
              <span className="truncate">{att.name}</span>
            </span>
          ))}
        </div>
      ) : null}
      <MessageActions align="end" meta={formatTime(message.timestamp)}>
        <CopyButton text={body} label="Copier le message" />
        {branch && branch.count > 1 ? (
          <div className="flex items-center text-xs text-fg-2 tabular-nums">
            <IconButton
              label="Version précédente"
              size="sm"
              disabled={busy || branch.current <= 0}
              onClick={() => navigate(message.mid, branch.current - 1)}
            >
              <ChevronLeft size={15} />
            </IconButton>
            <span className="px-0.5">
              {branch.current + 1}/{branch.count}
            </span>
            <IconButton
              label="Version suivante"
              size="sm"
              disabled={busy || branch.current >= branch.count - 1}
              onClick={() => navigate(message.mid, branch.current + 1)}
            >
              <ChevronRight size={15} />
            </IconButton>
          </div>
        ) : null}
      </MessageActions>
    </div>
  );
});
