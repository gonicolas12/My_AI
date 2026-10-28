/*
 * Appels d'outils de la page Code : ceux que l'extension VS Code exécute dans
 * son workspace (AGENT_TOOLS de core/agentic_executor.py), avec leur icône et
 * leur libellé (« Lecture de src/app.ts », « Commande npm test »).
 */

import {
  ExternalLink,
  FileCode2,
  FilePen,
  FilePlus,
  FileSearch,
  FileText,
  FolderOpen,
  Search,
  SquareTerminal,
  Wrench,
  type LucideIcon,
} from 'lucide-react';

import type { MessageKey, Translate } from '../../i18n';
import type { CodeToolCall } from '../../lib/events';

const TOOLS: Record<string, { icon: LucideIcon; label: MessageKey }> = {
  read_file: { icon: FileText, label: 'code.tool.read_file' },
  write_file: { icon: FilePlus, label: 'code.tool.write_file' },
  edit_file: { icon: FilePen, label: 'code.tool.edit_file' },
  list_dir: { icon: FolderOpen, label: 'code.tool.list_dir' },
  glob: { icon: FileSearch, label: 'code.tool.glob' },
  grep: { icon: Search, label: 'code.tool.grep' },
  run_command: { icon: SquareTerminal, label: 'code.tool.run_command' },
  get_active_editor: { icon: FileCode2, label: 'code.tool.get_active_editor' },
  open_file: { icon: ExternalLink, label: 'code.tool.open_file' },
};

/** Longueur d'une commande ou d'un motif dans le libellé */
const TARGET_LENGTH = 80;

export function codeToolIcon(name: string): LucideIcon {
  return TOOLS[name]?.icon ?? Wrench;
}

/** Ce que vise l'appel, sur une ligne : chemin, motif ou commande */
export function codeToolTarget(tool: Pick<CodeToolCall, 'name' | 'input'>): string {
  const input = tool.input;
  const value = (key: string) => {
    const field = input[key];
    return typeof field === 'string' ? field : '';
  };
  let target = '';
  if (tool.name === 'run_command') target = value('command');
  else if (tool.name === 'glob' || tool.name === 'grep') target = value('pattern');
  else target = value('path') || (tool.name === 'list_dir' ? '.' : '');
  const line = target.replace(/\s+/g, ' ').trim();
  return line.length > TARGET_LENGTH ? `${line.slice(0, TARGET_LENGTH)}…` : line;
}

export function codeToolLabel(tool: Pick<CodeToolCall, 'name' | 'input'>, t: Translate): string {
  const known = TOOLS[tool.name];
  if (!known) return tool.name;
  return t(known.label, { target: codeToolTarget(tool) });
}

/** Arguments à montrer dans le détail : la commande telle quelle, sinon le JSON */
export function codeToolInput(tool: Pick<CodeToolCall, 'name' | 'input'>): string {
  if (tool.name === 'run_command' && typeof tool.input.command === 'string') {
    return tool.input.command;
  }
  return JSON.stringify(tool.input, null, 2);
}
