import { CircleAlert, CircleCheck, Info, TriangleAlert, X } from 'lucide-react';

import { cn } from '../../lib/cn';
import type { NotificationLevel } from '../../lib/events';
import { withoutLeadingEmoji } from '../../lib/format';
import { dismissToast, useApp } from '../../stores/app';

const STYLES: Record<NotificationLevel, { icon: typeof Info; color: string }> = {
  info: { icon: Info, color: 'text-info' },
  success: { icon: CircleCheck, color: 'text-success' },
  warning: { icon: TriangleAlert, color: 'text-warning' },
  error: { icon: CircleAlert, color: 'text-error' },
};

/** Notifications brèves, en haut à droite (show_notification dans Tk) */
export function Toasts() {
  const toasts = useApp((state) => state.toasts);
  return (
    <div
      className="pointer-events-none fixed top-16 right-4 z-50 flex w-80 flex-col gap-2"
      aria-live="polite"
    >
      {toasts.map((toast) => {
        const { icon: Icon, color } = STYLES[toast.level];
        return (
          <div
            key={toast.id}
            role={toast.level === 'error' ? 'alert' : 'status'}
            className="pointer-events-auto flex items-start gap-2.5 rounded-md border border-line bg-bg-2 px-3 py-2.5 text-sm text-fg shadow-lg"
            style={{ animation: 'rise-in var(--motion) var(--motion-ease)' }}
          >
            <Icon size={16} className={cn('mt-0.5 shrink-0', color)} />
            <span className="min-w-0 flex-1 break-words">{withoutLeadingEmoji(toast.message)}</span>
            <button
              type="button"
              aria-label="Fermer"
              onClick={() => dismissToast(toast.id)}
              className="rounded-xs text-fg-3 hover:text-fg"
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </div>
  );
}
