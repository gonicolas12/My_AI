/*
 * Grand dialogue d'un panneau (Réglages, Mémoire, Prompts, Relay, Aide) :
 * en-tête avec icône, titre et croix, corps qui défile, pied facultatif.
 * Échap et un clic à l'extérieur le ferment.
 */

import * as RadixDialog from '@radix-ui/react-dialog';
import { X, type LucideIcon } from 'lucide-react';
import { type ReactNode, useRef } from 'react';

import { IconButton } from '../../components/ui/Button';
import { cn } from '../../lib/cn';

interface PanelDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  icon: LucideIcon;
  title: string;
  /** Sous-titre, sous le titre */
  description?: ReactNode;
  /** Éléments de l'en-tête, à gauche de la croix (onglets, actions) */
  actions?: ReactNode;
  footer?: ReactNode;
  children: ReactNode;
  /** Largeur maximale (px) */
  width?: number;
  /** Corps sans marges (listes qui gèrent les leurs) */
  flush?: boolean;
}

export function PanelDialog({
  open,
  onOpenChange,
  icon: Icon,
  title,
  description,
  actions,
  footer,
  children,
  width = 860,
  flush = false,
}: PanelDialogProps) {
  const contentRef = useRef<HTMLDivElement>(null);
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay
          className="fixed inset-0 z-40 bg-scrim"
          style={{ animation: 'fade-in var(--motion) var(--motion-ease)' }}
        />
        <RadixDialog.Content
          className={cn(
            'fixed top-1/2 left-1/2 z-50 flex w-[calc(100vw-32px)] -translate-x-1/2 -translate-y-1/2 flex-col',
            'h-[min(760px,calc(100vh-48px))] rounded-lg border border-line bg-bg-2 text-fg shadow-lg',
            'focus:outline-none',
          )}
          style={{ maxWidth: width, animation: 'rise-in var(--motion) var(--motion-ease)' }}
          onOpenAutoFocus={(event) => {
            // Focus sur le panneau, pas sur sa croix : son infobulle ne s'ouvre pas
            // d'elle-même (un champ avec autoFocus garde le sien)
            event.preventDefault();
            if (!contentRef.current?.contains(document.activeElement)) contentRef.current?.focus();
          }}
          ref={contentRef}
        >
          <header className="flex shrink-0 items-start gap-3 border-b border-line px-5 py-4">
            <span className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent">
              <Icon size={17} />
            </span>
            <div className="min-w-0 flex-1">
              <RadixDialog.Title className="text-lg leading-8 font-semibold">
                {title}
              </RadixDialog.Title>
              {description ? (
                <RadixDialog.Description className="text-sm text-fg-2">
                  {description}
                </RadixDialog.Description>
              ) : (
                <RadixDialog.Description className="sr-only">{title}</RadixDialog.Description>
              )}
            </div>
            {actions ? <div className="flex shrink-0 items-center gap-2">{actions}</div> : null}
            <RadixDialog.Close asChild>
              <IconButton label="Fermer" shortcut="Échap" tooltipSide="left">
                <X size={18} />
              </IconButton>
            </RadixDialog.Close>
          </header>
          <div className={cn('min-h-0 flex-1 overflow-y-auto', !flush && 'px-5 py-4')}>
            {children}
          </div>
          {footer ? (
            <footer className="flex shrink-0 items-center justify-end gap-2 border-t border-line px-5 py-3">
              {footer}
            </footer>
          ) : null}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
