import * as RadixTooltip from '@radix-ui/react-tooltip';
import type { ReactNode } from 'react';

export const TooltipProvider = RadixTooltip.Provider;

interface TooltipProps {
  label: ReactNode;
  /** Raccourci clavier affiché à droite du libellé */
  shortcut?: string | undefined;
  side?: 'top' | 'right' | 'bottom' | 'left';
  children: ReactNode;
}

export function Tooltip({ label, shortcut, side = 'bottom', children }: TooltipProps) {
  return (
    <RadixTooltip.Root>
      <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          side={side}
          sideOffset={6}
          className="z-50 flex items-center gap-2 rounded-sm border border-line bg-bg-3 px-2 py-1 text-xs text-fg shadow-md"
          style={{ animation: 'fade-in var(--motion-fast) var(--motion-ease)' }}
        >
          {label}
          {shortcut ? <kbd className="font-sans text-2xs text-fg-2">{shortcut}</kbd> : null}
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}
