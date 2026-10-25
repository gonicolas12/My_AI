/*
 * Palette de commandes (command_palette.py de Tk) : Ctrl+K l'ouvre ou la
 * ferme. Les 14 commandes de Tk, dans son ordre, plus « Changer de langue »,
 * filtrées par sous-chaîne du libellé et du raccourci ; flèches (en boucle),
 * Entrée ou clic l'exécutent après avoir fermé la palette ; Échap ou un clic
 * à côté la ferment.
 */

import * as RadixDialog from '@radix-ui/react-dialog';
import { Command } from 'cmdk';
import { Search } from 'lucide-react';
import { useMemo, useState } from 'react';

import { useT } from '../../i18n';
import { closePalette, usePalette } from '../../stores/palette';
import { filterCommands, PALETTE_COMMANDS, type ShownCommand, translateCommands } from './commands';

function Palette() {
  const t = useT();
  const commands = useMemo(() => translateCommands(PALETTE_COMMANDS, t), [t]);
  const [query, setQuery] = useState('');
  const [selected, setSelected] = useState<string>(PALETTE_COMMANDS[0]?.label ?? '');
  const shown = filterCommands(commands, query);

  const run = (command: ShownCommand) => {
    closePalette();
    command.run();
  };

  return (
    <Command
      label={t('palette.label')}
      shouldFilter={false}
      loop
      vimBindings={false}
      value={selected}
      onValueChange={setSelected}
      className="flex max-h-[min(640px,75vh)] flex-col"
    >
      <div className="flex shrink-0 items-center gap-3 border-b border-line px-4">
        <Search size={17} className="shrink-0 text-fg-3" />
        <Command.Input
          value={query}
          onValueChange={(value) => {
            setQuery(value);
            // Nouvelle liste : la première commande est choisie (Tk)
            setSelected(filterCommands(commands, value)[0]?.label ?? '');
          }}
          placeholder={t('palette.placeholder')}
          className="h-13 min-w-0 flex-1 bg-transparent text-base text-fg outline-none placeholder:text-fg-3"
        />
      </div>
      <Command.List className="min-h-0 overflow-y-auto p-1.5">
        {shown.length ? null : (
          <p className="px-3 py-6 text-center text-sm text-fg-3">{t('palette.empty')}</p>
        )}
        {shown.map((command) => (
          <Command.Item
            key={command.label}
            value={command.label}
            onSelect={() => run(command)}
            className="group flex h-10 cursor-pointer items-center gap-3 rounded-md px-3 text-sm text-fg data-[selected=true]:bg-accent data-[selected=true]:text-on-accent"
          >
            <span className="min-w-0 flex-1 truncate">{command.text}</span>
            {command.hintText ? (
              <kbd className="shrink-0 font-sans text-xs text-fg-3 group-data-[selected=true]:text-on-accent">
                {command.hintText}
              </kbd>
            ) : null}
          </Command.Item>
        ))}
      </Command.List>
    </Command>
  );
}

export function CommandPalette() {
  const t = useT();
  const open = usePalette((state) => state.open);
  return (
    <RadixDialog.Root
      open={open}
      onOpenChange={(value) => {
        if (!value) closePalette();
      }}
    >
      <RadixDialog.Portal>
        <RadixDialog.Content
          className="fixed top-[max(60px,14vh)] left-1/2 z-50 w-[min(640px,calc(100vw-32px))] -translate-x-1/2 overflow-hidden rounded-lg border border-line bg-bg-2 shadow-lg focus:outline-none"
          style={{ animation: 'fade-in var(--motion-fast) var(--motion-ease)' }}
        >
          <RadixDialog.Title className="sr-only">{t('palette.label')}</RadixDialog.Title>
          <RadixDialog.Description className="sr-only">
            {t('palette.description')}
          </RadixDialog.Description>
          {/* Remontée à chaque ouverture : recherche vide, première commande choisie */}
          {open ? <Palette /> : null}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
