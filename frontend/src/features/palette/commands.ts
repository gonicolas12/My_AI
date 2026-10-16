/*
 * Commandes de la palette (_build_command_list de Tk), dans son ordre, et leur
 * filtre : sous-chaîne, sans casse, du libellé et du raccourci.
 */

import {
  clearConversation,
  exportConversation,
  newConversation,
  saveConversation,
  setSidebarOpen,
  toggleSidebar,
} from '../../lib/actions';
import { setTab, useApp } from '../../stores/app';
import { openPanel } from '../../stores/panels';

export interface PaletteCommand {
  label: string;
  /** Raccourci affiché à droite, cherché aussi par le filtre */
  hint: string;
  run: () => void;
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

export const PALETTE_COMMANDS: PaletteCommand[] = [
  { label: 'Nouveau chat', hint: 'Ctrl+N', run: () => void newConversation() },
  { label: 'Effacer le chat', hint: 'Ctrl+L', run: () => void clearConversation() },
  { label: 'Sauvegarder la session', hint: 'Ctrl+S', run: () => void saveConversation() },
  { label: 'Afficher / masquer la barre latérale', hint: 'Ctrl+B', run: sidebar },
  { label: "Aller à l'onglet Chat", hint: '', run: () => setTab('chat') },
  { label: "Aller à l'onglet Agents", hint: '', run: () => setTab('agents') },
  { label: 'Relay (accès mobile)', hint: 'Ctrl+R', run: () => openPanel('relay') },
  { label: 'Réglages', hint: 'Ctrl+,', run: () => openPanel('settings') },
  { label: 'Mémoire', hint: '', run: () => openPanel('memory') },
  { label: 'Bibliothèque de prompts', hint: '', run: () => openPanel('prompts') },
  {
    label: 'Exporter la conversation (Markdown)',
    hint: '',
    run: () => void exportConversation('markdown'),
  },
  {
    label: 'Exporter la conversation (HTML)',
    hint: '',
    run: () => void exportConversation('html'),
  },
  { label: 'Exporter la conversation (PDF)', hint: '', run: () => void exportConversation('pdf') },
  { label: 'Aide', hint: 'F1', run: () => openPanel('help') },
];

/** Sous-chaîne, sans casse, du libellé et du raccourci ; ordre gardé (Tk) */
export function filterCommands(commands: PaletteCommand[], query: string): PaletteCommand[] {
  const needle = query.trim().toLowerCase();
  if (!needle) return commands;
  return commands.filter((command) =>
    `${command.label} ${command.hint}`.toLowerCase().includes(needle),
  );
}
