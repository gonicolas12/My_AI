import { Slash } from 'lucide-react';

import type { SlashCommand } from '../../lib/api';
import { cn } from '../../lib/cn';

interface SlashMenuProps {
  id: string;
  commands: SlashCommand[];
  active: number;
  onHover: (index: number) => void;
  onChoose: (command: SlashCommand) => void;
}

/** Liste des slash commands, au-dessus de la zone de saisie (le focus reste dans le texte) */
export function SlashMenu({ id, commands, active, onHover, onChoose }: SlashMenuProps) {
  return (
    <div
      id={id}
      role="listbox"
      aria-label="Commandes"
      className="absolute right-0 bottom-full left-0 z-30 mb-2 max-h-80 overflow-y-auto rounded-lg border border-line bg-bg-2 p-1 shadow-lg"
      style={{ animation: 'fade-in var(--motion-fast) var(--motion-ease)' }}
    >
      {commands.map((command, index) => (
        <div
          key={command.command}
          id={`${id}-${index}`}
          role="option"
          aria-selected={index === active}
          // Le clic ne retire pas le focus de la zone de saisie
          onMouseDown={(event) => event.preventDefault()}
          onMouseEnter={() => onHover(index)}
          onClick={() => onChoose(command)}
          className={cn(
            'flex cursor-pointer items-baseline gap-3 rounded-md px-3 py-2 text-sm',
            index === active ? 'bg-accent text-on-accent' : 'text-fg',
          )}
        >
          <span className="inline-flex shrink-0 items-center font-mono font-medium">
            <Slash size={12} className="mr-0.5 opacity-70" />
            {command.command}
          </span>
          <span className={cn('truncate', index === active ? 'text-on-accent' : 'text-fg-2')}>
            {command.title}
            {command.description ? (
              <span className={index === active ? 'opacity-80' : 'text-fg-3'}>
                {' '}
                · {command.description}
              </span>
            ) : null}
          </span>
        </div>
      ))}
    </div>
  );
}
