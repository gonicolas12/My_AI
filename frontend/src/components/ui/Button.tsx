import { forwardRef, type ButtonHTMLAttributes, type ReactNode } from 'react';

import { cn } from '../../lib/cn';
import { Tooltip } from './Tooltip';

type Variant = 'primary' | 'secondary' | 'ghost' | 'danger';
type Size = 'sm' | 'md';

const VARIANTS: Record<Variant, string> = {
  primary: 'bg-accent text-on-accent hover:bg-accent-hover disabled:bg-line-2 disabled:text-fg-2',
  secondary: 'border border-line bg-bg-2 text-fg hover:bg-bg-3 disabled:text-fg-3',
  ghost: 'text-fg-2 hover:bg-hover hover:text-fg disabled:text-fg-3 disabled:hover:bg-transparent',
  danger: 'bg-error text-fg hover:opacity-90 disabled:opacity-50',
};

const SIZES: Record<Size, string> = {
  sm: 'h-8 px-3 text-sm gap-1.5',
  md: 'h-9 px-4 text-sm gap-2',
};

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { variant = 'secondary', size = 'md', className, type = 'button', ...props },
  ref,
) {
  return (
    <button
      ref={ref}
      type={type}
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-md font-medium transition-colors duration-150 select-none',
        VARIANTS[variant],
        SIZES[size],
        className,
      )}
      {...props}
    />
  );
});

interface IconButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  label: string;
  shortcut?: string | undefined;
  tooltipSide?: 'top' | 'right' | 'bottom' | 'left';
  active?: boolean;
  size?: 'sm' | 'md' | 'lg';
  children: ReactNode;
}

const ICON_SIZES = { sm: 'h-7 w-7', md: 'h-8 w-8', lg: 'h-9 w-9' };

/** Bouton à icône, avec son libellé en infobulle (et pour les lecteurs d'écran) */
export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(function IconButton(
  {
    label,
    shortcut,
    tooltipSide,
    active,
    size = 'md',
    className,
    type = 'button',
    children,
    ...props
  },
  ref,
) {
  const button = (
    <button
      ref={ref}
      type={type}
      aria-label={label}
      className={cn(
        'inline-flex shrink-0 items-center justify-center rounded-md text-fg-2 transition-colors duration-150',
        'hover:bg-hover hover:text-fg disabled:text-fg-3 disabled:hover:bg-transparent',
        active && 'bg-active text-fg',
        ICON_SIZES[size],
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
  return (
    <Tooltip label={label} shortcut={shortcut} side={tooltipSide}>
      {props.disabled ? <span className="inline-flex">{button}</span> : button}
    </Tooltip>
  );
});
