import * as RadixTooltip from '@radix-ui/react-tooltip';
import { type ReactNode, useEffect, useState } from 'react';

import { isRtl, shortcutLabel, useLocale, useT } from '../../i18n';

export const TooltipProvider = RadixTooltip.Provider;

/*
 * Une infobulle s'ouvre au survol, ou au focus quand on navigue au clavier (Tab).
 * Radix l'ouvre aussi quand le focus revient seul sur son bouton (fenêtre
 * réactivée, qui rend le focus au dernier bouton cliqué) : elle restait alors
 * affichée, faute d'un départ de la souris pour la refermer. Ce focus-là ne
 * l'ouvre plus.
 */
let keyboardNavigation = false;
if (typeof window !== 'undefined') {
  window.addEventListener(
    'keydown',
    (event) => {
      if (event.key === 'Tab') keyboardNavigation = true;
    },
    true,
  );
  window.addEventListener(
    'pointerdown',
    () => {
      keyboardNavigation = false;
    },
    true,
  );
  window.addEventListener('blur', () => {
    keyboardNavigation = false;
  });
}

interface TooltipProps {
  label: ReactNode;
  /** Raccourci clavier affiché à droite du libellé */
  shortcut?: string | undefined;
  side?: 'top' | 'right' | 'bottom' | 'left';
  children: ReactNode;
}

export function Tooltip({ label, shortcut, side = 'bottom', children }: TooltipProps) {
  const t = useT();
  // De droite à gauche (arabe), une infobulle « à droite » passe à gauche, du côté du texte
  const mirrored = isRtl(useLocale());
  const placed =
    mirrored && side === 'left' ? 'right' : mirrored && side === 'right' ? 'left' : side;
  const [open, setOpen] = useState(false);
  // Fenêtre quittée : l'infobulle se ferme, sans attendre un départ de la souris
  useEffect(() => {
    if (!open) return undefined;
    const close = () => setOpen(false);
    window.addEventListener('blur', close);
    return () => window.removeEventListener('blur', close);
  }, [open]);
  return (
    <RadixTooltip.Root open={open} onOpenChange={setOpen}>
      <RadixTooltip.Trigger
        asChild
        onFocus={(event) => {
          // Focus rendu sans navigation au clavier : Radix n'ouvre pas l'infobulle
          if (!keyboardNavigation) event.preventDefault();
        }}
      >
        {children}
      </RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          side={placed}
          sideOffset={6}
          className="fade-in-fast z-50 flex items-center gap-2 rounded-sm border border-line bg-bg-3 px-2 py-1 text-xs text-fg shadow-md"
        >
          {label}
          {shortcut ? (
            <kbd className="font-sans text-2xs text-fg-2">{shortcutLabel(shortcut, t)}</kbd>
          ) : null}
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}
