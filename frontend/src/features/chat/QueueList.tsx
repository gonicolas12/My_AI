import { Clock, Smartphone, X } from 'lucide-react';

import { cancelQueued } from '../../lib/actions';
import { useChat } from '../../stores/chat';
import { splitAttachmentLines } from './attachments';

/** Messages en attente dans la file commune au desktop et au mobile (D1) */
export function QueueList() {
  const queue = useChat((state) => state.queue);
  if (!queue.length) return null;
  return (
    <div className="mb-2 rounded-lg border border-line bg-bg-2/70 px-3 py-2">
      <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-fg-2">
        <Clock size={13} />
        En attente · {queue.length}
      </div>
      <ul className="space-y-1">
        {queue.map((item) => (
          <li key={item.request_id} className="flex items-center gap-2 text-sm text-fg-2">
            {item.source === 'mobile' ? (
              <Smartphone size={13} className="shrink-0 text-fg-3" aria-label="Mobile" />
            ) : null}
            <span className="min-w-0 flex-1 truncate">{splitAttachmentLines(item.text).body}</span>
            <button
              type="button"
              aria-label="Retirer de la file"
              onClick={() => void cancelQueued(item.request_id)}
              className="rounded-xs p-0.5 text-fg-3 hover:bg-hover hover:text-fg"
            >
              <X size={13} />
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}
