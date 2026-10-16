import { Brain, ChevronRight } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { cn } from '../../lib/cn';
import { formatDuration } from '../../lib/format';

interface ReasoningProps {
  text: string;
  /** Jetons de réflexion en cours de réception */
  active: boolean;
  /** Durée totale de la réflexion, une fois terminée */
  durationMs?: number | undefined;
  /** Réponse en cours (sinon réponse terminée, repliée par défaut) */
  live: boolean;
}

/**
 * Bloc « Réflexion » repliable (mode thinking) : déplié pendant la
 * réflexion, comme dans l'interface Tk, puis replié une fois la réponse
 * commencée, sauf si l'utilisateur l'a ouvert ou fermé lui-même.
 */
export function Reasoning({ text, active, durationMs, live }: ReasoningProps) {
  const [manual, setManual] = useState<boolean | null>(null);
  // Rien à déplier tant qu'aucun texte de réflexion n'est arrivé
  const hasText = text.trim().length > 0;
  const open = hasText && (manual ?? (live && active));
  const body = useRef<HTMLDivElement>(null);

  // Le texte suit la réflexion tant qu'elle s'écrit
  useEffect(() => {
    const el = body.current;
    if (el && active) el.scrollTop = el.scrollHeight;
  }, [text, active]);

  const waiting = live && active;
  const duration = !waiting && durationMs ? formatDuration(durationMs) : '';

  return (
    <div className="mb-3">
      <button
        type="button"
        onClick={() => setManual(!open)}
        disabled={!hasText}
        aria-expanded={hasText ? open : undefined}
        className="group inline-flex items-center gap-1.5 rounded-sm py-1 pr-2 text-sm text-fg-2 transition-colors hover:text-fg"
      >
        <Brain size={15} className={cn('shrink-0', waiting && 'text-accent pulse-soft')} />
        <span className={cn(waiting && 'shimmer')}>Réflexion</span>
        {duration ? <span className="text-fg-3">· {duration}</span> : null}
        {hasText ? (
          <ChevronRight
            size={14}
            className={cn('shrink-0 transition-transform duration-150', open && 'rotate-90')}
          />
        ) : null}
      </button>
      {open && text ? (
        <div
          ref={body}
          className="mt-1 max-h-80 overflow-y-auto border-l-2 border-line pl-3 text-sm leading-relaxed whitespace-pre-wrap text-fg-2"
          style={{ animation: 'fade-in var(--motion) var(--motion-ease)' }}
        >
          {text.trim()}
        </div>
      ) : null}
    </div>
  );
}
