import * as RadixMenu from '@radix-ui/react-dropdown-menu';
import type { ReactNode } from 'react';

import { cn } from '../../lib/cn';

export const Menu = RadixMenu.Root;
export const MenuTrigger = RadixMenu.Trigger;

interface MenuContentProps {
  children: ReactNode;
  side?: 'top' | 'right' | 'bottom' | 'left';
  align?: 'start' | 'center' | 'end';
  label?: string;
}

/** Menu déroulant (clavier, Échap et clic à l'extérieur gérés par Radix) */
export function MenuContent({
  children,
  side = 'bottom',
  align = 'start',
  label,
}: MenuContentProps) {
  return (
    <RadixMenu.Portal>
      <RadixMenu.Content
        side={side}
        align={align}
        sideOffset={6}
        aria-label={label}
        className="fade-in-fast z-50 min-w-48 rounded-md border border-line bg-bg-2 p-1 text-sm text-fg shadow-lg"
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

export function MenuSeparator() {
  return <RadixMenu.Separator className="my-1 h-px bg-line" />;
}
