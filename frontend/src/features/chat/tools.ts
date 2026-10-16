/*
 * Appels d'outils : icône et libellé affichés.
 *
 * Le libellé vient du serveur (core/chat_service.py, tool_label, repris de
 * l'interface Tk) ; son emoji de tête est remplacé ici par une icône.
 */

import {
  Brain,
  Calculator,
  Code2,
  FileSearch,
  FilePen,
  FileText,
  FolderOpen,
  FolderPlus,
  MoveRight,
  PenLine,
  Search,
  Sparkles,
  Trash2,
  Wrench,
  type LucideIcon,
} from 'lucide-react';

import type { ToolCallView } from '../../lib/events';

const ICONS: Record<string, LucideIcon> = {
  web_search: Search,
  search_memory: Brain,
  remember_fact: Brain,
  read_local_file: FileText,
  list_directory: FolderOpen,
  generate_code: Code2,
  generate_document: FileText,
  edit_document: FilePen,
  calculate: Calculator,
  search_local_files: FileSearch,
  write_local_file: PenLine,
  move_local_file: MoveRight,
  delete_local_file: Trash2,
  create_directory: FolderPlus,
  synthesis: Sparkles,
};

export function toolIcon(name: string): LucideIcon {
  return ICONS[name] ?? Wrench;
}

/** Libellé sans l'emoji de tête (« 🔍 Recherche… » → « Recherche… ») */
export function toolText(label: string): string {
  const match = /^[^\p{L}\p{N}«"'(]+/u.exec(label);
  return match ? label.slice(match[0].length) : label;
}

/** Résumé court d'un outil terminé (« 3 sources ») */
export function toolOutcome(tool: ToolCallView): string | null {
  if (tool.ok === undefined) return null;
  if (tool.name === 'web_search' && tool.ok) {
    const count = tool.sources ?? 0;
    return count ? `${count} source${count > 1 ? 's' : ''}` : 'aucune source';
  }
  return null;
}
