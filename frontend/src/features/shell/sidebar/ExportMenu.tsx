/*
 * Export de la conversation (section « Export » de Tk) : Markdown, HTML ou
 * PDF, vers le fichier choisi dans le dialogue du système ; dans un
 * navigateur, dans outputs/exports/.
 */

import { Download, FileCode2, FileText, FileType } from 'lucide-react';

import { IconButton } from '../../../components/ui/Button';
import { Menu, MenuContent, MenuItem, MenuTrigger } from '../../../components/ui/Menu';
import { exportConversation } from '../../../lib/actions';
import type { ExportFormat } from '../../../lib/api';

const FORMATS: { format: ExportFormat; label: string; icon: typeof FileText }[] = [
  { format: 'markdown', label: 'Markdown (.md)', icon: FileType },
  { format: 'html', label: 'HTML (.html)', icon: FileCode2 },
  { format: 'pdf', label: 'PDF (.pdf)', icon: FileText },
];

export function ExportMenu() {
  return (
    <Menu>
      <MenuTrigger asChild>
        <IconButton label="Exporter la conversation" tooltipSide="top">
          <Download size={17} />
        </IconButton>
      </MenuTrigger>
      <MenuContent side="top" align="end" label="Exporter">
        {FORMATS.map(({ format, label, icon: Icon }) => (
          <MenuItem
            key={format}
            icon={<Icon size={15} />}
            onSelect={() => void exportConversation(format)}
          >
            {label}
          </MenuItem>
        ))}
      </MenuContent>
    </Menu>
  );
}
