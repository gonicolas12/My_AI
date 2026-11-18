/*
 * Grand dialogue d'un panneau (Réglages, Mémoire, Prompts, Relay, Aide) :
 * en-tête avec icône, titre et croix, corps qui défile, pied facultatif.
 * Échap et un clic à l'extérieur le ferment.
 *
 * Un panneau peut recevoir des fichiers glissés (onglet Documents de la
 * Mémoire) : déposés sur lui ou sur le voile qui l'entoure ; pendant le
 * survol, son contour s'éclaire en orange.
 *
 * Un volet peut s'ouvrir à sa droite (aperçu d'un document de la Mémoire) : le
 * panneau s'élargit en douceur pour lui faire place, et se resserre quand il
 * se referme (asideClosing), jamais d'un coup.
 */

import * as RadixDialog from '@radix-ui/react-dialog';
import { X, type LucideIcon } from 'lucide-react';
import { type DragEvent, type ReactNode, useEffect, useRef, useState } from 'react';

import { IconButton } from '../../components/ui/Button';
import { useT } from '../../i18n';
import { cn } from '../../lib/cn';

/** Gestionnaires d'un dépôt de fichiers (useFileDrop) */
export interface PanelDropTarget {
  onDragOver(event: DragEvent): void;
  onDrop(event: DragEvent): void;
}

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
  /** Échap : event.preventDefault() garde le panneau ouvert (annuler une saisie) */
  onEscapeKeyDown?: (event: KeyboardEvent) => void;
  /** Fichiers déposés sur le panneau ou sur le voile autour */
  dropTarget?: PanelDropTarget | undefined;
  /** Des fichiers survolent la fenêtre : contour orange, halo */
  glow?: boolean;
  /** Volet à droite du panneau, sur toute sa hauteur (aperçu) */
  aside?: ReactNode;
  /** Le volet se referme : il se replie, le panneau se resserre */
  asideClosing?: boolean;
}

/** Largeur du volet de droite : 560 px, moins sur un petit écran */
const ASIDE_WIDTH = 'min(560px, 45vw)';

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
  onEscapeKeyDown,
  dropTarget,
  glow = false,
  aside,
  asideClosing = false,
}: PanelDialogProps) {
  const t = useT();
  const contentRef = useRef<HTMLDivElement>(null);
  const headerRef = useRef<HTMLElement>(null);
  const hasAside = Boolean(aside);
  const widened = hasAside && !asideClosing;
  // Hauteur de l'en-tête du panneau : celui du volet s'aligne sur lui (--aside-header)
  const [headerHeight, setHeaderHeight] = useState<number | null>(null);
  useEffect(() => {
    const header = headerRef.current;
    if (!header || !hasAside || typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(() => setHeaderHeight(header.offsetHeight));
    observer.observe(header);
    return () => observer.disconnect();
  }, [hasAside]);
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay
          {...dropTarget}
          className="fixed inset-0 z-40 bg-scrim"
          style={{ animation: 'fade-in var(--motion) var(--motion-ease)' }}
        />
        <RadixDialog.Content
          {...dropTarget}
          className={cn(
            'fixed top-1/2 left-1/2 z-50 flex w-[calc(100vw-32px)] -translate-x-1/2 -translate-y-1/2',
            'h-[min(760px,calc(100vh-48px))] rounded-lg border bg-bg-2 text-fg',
            'transition-[border-color,box-shadow,max-width] duration-150 focus:outline-none',
            glow ? 'drop-glow border-accent' : 'border-line shadow-lg',
          )}
          style={{
            // Volet ouvert : le panneau s'élargit d'autant, au rythme du volet
            maxWidth: widened ? `calc(${width}px + ${ASIDE_WIDTH})` : width,
            transitionDuration: '150ms, 150ms, var(--motion-pane)',
            transitionTimingFunction: 'var(--motion-ease)',
            animation: 'rise-in var(--motion) var(--motion-ease)',
          }}
          onEscapeKeyDown={onEscapeKeyDown}
          onOpenAutoFocus={(event) => {
            // Focus sur le panneau, pas sur sa croix : son infobulle ne s'ouvre pas
            // d'elle-même (un champ avec autoFocus garde le sien)
            event.preventDefault();
            if (!contentRef.current?.contains(document.activeElement)) contentRef.current?.focus();
          }}
          ref={contentRef}
        >
          <div className="flex min-w-0 flex-1 flex-col">
            <header
              ref={headerRef}
              className="flex shrink-0 items-start gap-3 border-b border-line px-5 py-4"
            >
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
                <IconButton label={t('panel.close')} shortcut="Escape" tooltipSide="left">
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
          </div>
          {aside ? (
            <aside
              className={cn(
                'h-full shrink-0 overflow-hidden rounded-e-lg border-s border-line bg-bg-2',
                asideClosing ? 'pane-close' : 'pane-open',
              )}
              style={{ width: ASIDE_WIDTH }}
            >
              {/* Contenu à sa largeur finale : il ne se recompose pas pendant que le volet s'ouvre */}
              <div
                className="flex h-full flex-col"
                style={
                  {
                    width: ASIDE_WIDTH,
                    '--aside-header': headerHeight ? `${headerHeight}px` : undefined,
                  } as React.CSSProperties
                }
              >
                {aside}
              </div>
            </aside>
          ) : null}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
