import * as RadixMenu from '@radix-ui/react-dropdown-menu';
import type { ReactNode, RefObject } from 'react';
import { createPortal } from 'react-dom';

import { cn } from '../../lib/cn';
import type { MenuPoint } from './useContextMenu';

const CONTENT_CLASS =
  'fade-in-fast z-50 min-w-48 rounded-md border border-line bg-bg-2 p-1 text-sm text-fg shadow-lg';

export const Menu = RadixMenu.Root;
export const MenuTrigger = RadixMenu.Trigger;

interface MenuContentProps {
  children: ReactNode;
  side?: 'top' | 'right' | 'bottom' | 'left';
  align?: 'start' | 'center' | 'end';
  label?: string;
  className?: string;
}

/** Menu déroulant (clavier, Échap et clic à l'extérieur gérés par Radix) */
export function MenuContent({
  children,
  side = 'bottom',
  align = 'start',
  label,
  className,
}: MenuContentProps) {
  return (
    <RadixMenu.Portal>
      <RadixMenu.Content
        side={side}
        align={align}
        sideOffset={6}
        aria-label={label}
        className={cn(CONTENT_CLASS, className)}
      >
        {children}
      </RadixMenu.Content>
    </RadixMenu.Portal>
  );
}

interface MenuItemProps {
  icon?: ReactNode;
  children: ReactNode;
  onSelect: () => void;
  disabled?: boolean;
  hint?: string;
}

export function MenuItem({ icon, children, onSelect, disabled, hint }: MenuItemProps) {
  return (
    <RadixMenu.Item
      onSelect={onSelect}
      disabled={disabled}
      className={cn(
        'flex cursor-pointer items-center gap-2.5 rounded-sm px-2.5 py-1.5 outline-none select-none',
        'data-[disabled]:cursor-default data-[disabled]:text-fg-3',
        'data-[highlighted]:bg-hover data-[highlighted]:text-fg',
      )}
    >
      {icon ? <span className="flex w-4 shrink-0 justify-center text-fg-2">{icon}</span> : null}
      <span className="flex-1">{children}</span>
      {hint ? <span className="text-2xs text-fg-3">{hint}</span> : null}
    </RadixMenu.Item>
  );
}

/**
 * Lien du menu : un vrai lien, ouvert dans le navigateur du système par le
 * gardien de navigation (installNavigationGuard), au clic comme à Entrée.
 */
export function MenuLink({
  href,
  icon,
  children,
  title,
}: {
  href: string;
  icon?: ReactNode;
  children: ReactNode;
  title?: string;
}) {
  return (
    <RadixMenu.Item
      asChild
      className="flex cursor-pointer items-center gap-2.5 rounded-sm px-2.5 py-1.5 outline-none select-none data-[highlighted]:bg-hover"
    >
      <a href={href} target="_blank" rel="noreferrer noopener" title={title}>
        {icon ? <span className="flex shrink-0 justify-center">{icon}</span> : null}
        <span className="min-w-0 flex-1 truncate text-link underline decoration-link/45 underline-offset-2">
          {children}
        </span>
      </a>
    </RadixMenu.Item>
  );
}

export function MenuSeparator() {
  return <RadixMenu.Separator className="my-1 h-px bg-line" />;
}

/**
 * Menu du clic droit (position : useContextMenu) : le menu déroulant, ancré sur
 * un point invisible posé sous le pointeur (pas de @radix-ui/react-context-menu) ;
 * fermé, il rend le focus à l'élément cliqué
 */
export function ContextMenu({
  at,
  onClose,
  origin,
  label,
  children,
}: {
  at: MenuPoint | null;
  onClose: () => void;
  origin?: RefObject<HTMLElement | null>;
  label?: string;
  children: ReactNode;
}) {
  if (!at) return null;
  return createPortal(
    <RadixMenu.Root
      open
      onOpenChange={(open) => {
        if (!open) onClose();
      }}
    >
      <RadixMenu.Trigger asChild>
        <span
          aria-hidden="true"
          className="pointer-events-none fixed size-0"
          style={{ left: at.x, top: at.y }}
        />
      </RadixMenu.Trigger>
      <RadixMenu.Portal>
        <RadixMenu.Content
          side="bottom"
          align="start"
          sideOffset={2}
          aria-label={label}
          // Nommé par label, pas par l'ancre invisible et vide que Radix lui donnerait
          aria-labelledby={undefined}
          onCloseAutoFocus={(event) => {
            event.preventDefault();
            origin?.current?.focus();
          }}
          className={CONTENT_CLASS}
        >
          {children}
        </RadixMenu.Content>
      </RadixMenu.Portal>
    </RadixMenu.Root>,
    document.body,
  );
}
