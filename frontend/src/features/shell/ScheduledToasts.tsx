/*
 * Fin d'une tâche planifiée (_show_scheduled_toast de Tk) : petit toast en bas
 * à droite pendant 6 s, liseré vert, orange ou rouge selon le statut ; un clic
 * ouvre le rapport de la tâche (fichier produit par l'appli).
 */

import { DismissableLayerBranch } from '@radix-ui/react-dismissable-layer';
import { CalendarClock, X } from 'lucide-react';

import { openFile } from '../../lib/actions';
import { cn } from '../../lib/cn';
import { dismissScheduledToast, type ScheduledToast, useApp } from '../../stores/app';

/** Liseré selon le statut de la tâche (couleurs de Tk) */
function stripe(status: string): string {
  if (status === 'success') return 'border-l-success';
  if (status === 'partial' || status === 'interrupted') return 'border-l-warning';
  return 'border-l-error';
}

/** Résumé, sinon statut ; 160 caractères au plus (Tk) */
function summaryOf(toast: ScheduledToast): string {
  const text = (toast.summary || toast.status_text || '').trim();
  return text.length > 160 ? `${text.slice(0, 157)}…` : text;
}

export function ScheduledToasts() {
  const toasts = useApp((state) => state.scheduledToasts);
  if (!toasts.length) return null;
  return (
    // Au-dessus des dialogues (z-60) ; pour Radix, une « branche » de chaque dialogue :
    // un clic sur un toast ne ferme pas le dialogue ouvert
    <DismissableLayerBranch
      className="pointer-events-none fixed right-4 bottom-4 z-60 flex w-80 flex-col gap-2"
      aria-live="polite"
      data-toast-region
    >
      {toasts.map((toast) => {
        const text = summaryOf(toast);
        const open = () => {
          if (toast.output_file) void openFile(toast.output_file);
          dismissScheduledToast(toast.id);
        };
        return (
          <div
            key={toast.id}
            role="status"
            className={cn(
              'pointer-events-auto flex items-start gap-2.5 rounded-md border border-l-4 border-line bg-bg-2 py-2.5 pr-2 pl-3 text-sm shadow-lg',
              stripe(toast.status),
            )}
            style={{ animation: 'rise-in var(--motion) var(--motion-ease)' }}
          >
            <button
              type="button"
              onClick={open}
              title={toast.output_file ? 'Ouvrir le rapport' : undefined}
              className="flex min-w-0 flex-1 items-start gap-2.5 text-left"
            >
              <CalendarClock size={16} className="mt-0.5 shrink-0 text-fg-2" />
              <span className="min-w-0 flex-1">
                <span className="block truncate font-semibold text-fg">
                  {toast.name || 'Tâche planifiée'}
                </span>
                {text ? (
                  // Texte brut du résumé (D47) : ses lignes restent des lignes
                  <span className="mt-0.5 block text-xs whitespace-pre-line text-fg-2">{text}</span>
                ) : null}
              </span>
            </button>
            <button
              type="button"
              aria-label="Fermer"
              onClick={() => dismissScheduledToast(toast.id)}
              className="rounded-xs text-fg-3 hover:text-fg"
            >
              <X size={14} />
            </button>
          </div>
        );
      })}
    </DismissableLayerBranch>
  );
}
