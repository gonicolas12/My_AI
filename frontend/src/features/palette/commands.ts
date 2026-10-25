/*
 * Commandes de la palette (_build_command_list de Tk), dans son ordre, plus
 * « Changer de langue », et leur filtre : sous-chaîne, sans casse, du libellé
 * traduit et du raccourci.
 */

import {
  clearConversation,
  exportConversation,
  newConversation,
  saveConversation,
  setSidebarOpen,
  toggleSidebar,
} from '../../lib/actions';
import { LOCALES, type MessageKey, shortcutLabel, type Translate } from '../../i18n';
import { setTab, useApp } from '../../stores/app';
import { openPanel } from '../../stores/panels';

export interface PaletteCommand {
  /** Clé du libellé (unique : sert aussi de valeur à la liste) */
  label: MessageKey;
  /** Raccourci affiché à droite (en anglais, cf. shortcutLabel), cherché aussi par le filtre */
  hint: string;
  /** Mots cherchés en plus du libellé */
  keywords?: string;
  run: () => void;
}

/** Commande dans la langue de l'interface */
export interface ShownCommand extends PaletteCommand {
  text: string;
  hintText: string;
}

/** Barre latérale : sur l'onglet Agents, qui n'en a pas, retour au Chat avec la barre ouverte */
function sidebar(): void {
  if (useApp.getState().tab !== 'chat') {
    setTab('chat');
    setSidebarOpen(true);
    return;
  }
  toggleSidebar();
}

/**
 * La langue se retrouve quelle que soit celle de l'interface : « language »,
 * « idioma », « Sprache »… et le nom de chaque langue
 */
const LANGUAGE_KEYWORDS = [
  'language langue idioma sprache lingua língua taal язык 语言 言語 언어 اللغة',
  ...LOCALES.map((locale) => locale.name),
].join(' ');

export const PALETTE_COMMANDS: PaletteCommand[] = [
  { label: 'palette.newChat', hint: 'Ctrl+N', run: () => void newConversation() },
  { label: 'palette.clearChat', hint: 'Ctrl+L', run: () => void clearConversation() },
  { label: 'palette.saveSession', hint: 'Ctrl+S', run: () => void saveConversation() },
  { label: 'palette.toggleSidebar', hint: 'Ctrl+B', run: sidebar },
  { label: 'palette.goChat', hint: '', run: () => setTab('chat') },
  { label: 'palette.goAgents', hint: '', run: () => setTab('agents') },
  { label: 'palette.relay', hint: 'Ctrl+R', run: () => openPanel('relay') },
  { label: 'palette.settings', hint: 'Ctrl+,', run: () => openPanel('settings') },
  {
    label: 'palette.language',
    hint: '',
    keywords: LANGUAGE_KEYWORDS,
    run: () => openPanel('settings'),
  },
  { label: 'palette.memory', hint: '', run: () => openPanel('memory') },
  { label: 'palette.prompts', hint: '', run: () => openPanel('prompts') },
  { label: 'palette.exportMarkdown', hint: '', run: () => void exportConversation('markdown') },
  { label: 'palette.exportHtml', hint: '', run: () => void exportConversation('html') },
  { label: 'palette.exportPdf', hint: '', run: () => void exportConversation('pdf') },
  { label: 'palette.help', hint: 'F1', run: () => openPanel('help') },
];

export function translateCommands(commands: PaletteCommand[], t: Translate): ShownCommand[] {
  return commands.map((command) => ({
    ...command,
    text: t(command.label),
    hintText: command.hint ? shortcutLabel(command.hint, t) : '',
  }));
}

/** Sous-chaîne, sans casse, du libellé et du raccourci ; ordre gardé (Tk) */
export function filterCommands(commands: ShownCommand[], query: string): ShownCommand[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return commands;
  return commands.filter((command) =>
    [command.text, command.hint, command.hintText, command.keywords ?? '']
      .join(' ')
      .toLowerCase()
      .includes(needle),
  );
}
