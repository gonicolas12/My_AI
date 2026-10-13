import * as RadixDialog from '@radix-ui/react-dialog';
import type { ReactNode } from 'react';

import { cn } from '../../lib/cn';

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: ReactNode;
  children?: ReactNode;
  footer?: ReactNode;
  /** Largeur maximale (px) */
  width?: number;
  /** Fermeture par Échap ou clic à l'extérieur */
  dismissible?: boolean;
}

/** Dialogue interne à la fenêtre (jamais une seconde fenêtre) */
export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  width = 440,
  dismissible = true,
}: DialogProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay
          className="fixed inset-0 z-40 bg-scrim"
          style={{ animation: 'fade-in var(--motion) var(--motion-ease)' }}
        />
        <RadixDialog.Content
          onEscapeKeyDown={(event) => {
            if (!dismissible) event.preventDefault();
          }}
          onPointerDownOutside={(event) => {
            if (!dismissible) event.preventDefault();
          }}
          className={cn(
            'fixed top-1/2 left-1/2 z-50 w-[calc(100vw-32px)] -translate-x-1/2 -translate-y-1/2',
            'rounded-lg border border-line bg-bg-2 p-5 text-fg shadow-lg focus:outline-none',
          )}
          style={{ maxWidth: width, animation: 'rise-in var(--motion) var(--motion-ease)' }}
        >
          <RadixDialog.Title className="text-lg font-semibold">{title}</RadixDialog.Title>
          {description ? (
            <RadixDialog.Description className="mt-2 text-sm text-fg-2">
              {description}
            </RadixDialog.Description>
          ) : (
            <RadixDialog.Description className="sr-only">{title}</RadixDialog.Description>
          )}
          {children ? <div className="mt-4">{children}</div> : null}
          {footer ? <div className="mt-5 flex justify-end gap-2">{footer}</div> : null}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
