/*
 * Export de la conversation (section « Export » de Tk) : Markdown, HTML ou
 * PDF, vers le fichier choisi dans le dialogue du système ; dans un
 * navigateur, dans outputs/exports/.
 */

import { Download, FileCode2, FileText, FileType } from 'lucide-react';

import { IconButton } from '../../../components/ui/Button';
import { Menu, MenuContent, MenuItem, MenuTrigger } from '../../../components/ui/Menu';
import { api, type ExportFormat } from '../../../lib/api';
import { shell } from '../../../lib/shell';
import { notify } from '../../../stores/app';

const FORMATS: { format: ExportFormat; label: string; extension: string; icon: typeof FileText }[] =
  [
    { format: 'markdown', label: 'Markdown (.md)', extension: 'md', icon: FileType },
    { format: 'html', label: 'HTML (.html)', extension: 'html', icon: FileCode2 },
    { format: 'pdf', label: 'PDF (.pdf)', extension: 'pdf', icon: FileText },
  ];

async function exportAs(format: ExportFormat, extension: string): Promise<void> {
  let path: string | null = null;
  if (shell.canPickFiles()) {
    path = await shell.saveFile(`conversation.${extension}`, format);
    if (!path) return; // dialogue annulé
  }
  try {
    const result = await api.exportConversation(format, path);
    notify('success', `✅ Exporté en ${format.toUpperCase()} : ${result.path}`);
  } catch (error) {
    notify('error', error instanceof Error ? error.message : String(error));
  }
}

export function ExportMenu() {
  return (
    <Menu>
      <MenuTrigger asChild>
        <IconButton label="Exporter la conversation" tooltipSide="top">
          <Download size={17} />
        </IconButton>
      </MenuTrigger>
      <MenuContent side="top" align="end" label="Exporter">
        {FORMATS.map(({ format, label, extension, icon: Icon }) => (
          <MenuItem
            key={format}
            icon={<Icon size={15} />}
            onSelect={() => void exportAs(format, extension)}
          >
            {label}
          </MenuItem>
        ))}
      </MenuContent>
    </Menu>
  );
}
