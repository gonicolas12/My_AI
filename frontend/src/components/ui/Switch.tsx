import * as RadixSwitch from '@radix-ui/react-switch';

import { cn } from '../../lib/cn';

interface SwitchProps {
  checked: boolean;
  onCheckedChange: (checked: boolean) => void;
  /** Libellé lu par les lecteurs d'écran (le texte visible est à côté) */
  label: string;
  disabled?: boolean;
  id?: string;
}

/** Interrupteur (réglage activé ou non) */
export function Switch({ checked, onCheckedChange, label, disabled, id }: SwitchProps) {
  return (
    <RadixSwitch.Root
      id={id}
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      aria-label={label}
      className={cn(
        'relative inline-flex h-5 w-9 shrink-0 items-center rounded-full transition-colors duration-150',
        'bg-line-2 data-[state=checked]:bg-accent disabled:opacity-50',
      )}
    >
      <RadixSwitch.Thumb className="block h-4 w-4 translate-x-0.5 rounded-full bg-fg shadow transition-transform duration-150 data-[state=checked]:translate-x-[18px]" />
    </RadixSwitch.Root>
  );
}
