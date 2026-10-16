/* Types de pièces jointes : entrées du menu « + » et icône de chaque type */

import {
  FileCode2,
  FileSpreadsheet,
  FileText,
  FileType,
  ImageIcon,
  Paperclip,
  Presentation,
  type LucideIcon,
} from 'lucide-react';

import type { AttachKind } from '../../lib/shell';

export const ATTACH_ENTRIES: { kind: AttachKind; label: string; icon: LucideIcon }[] = [
  { kind: 'PDF', label: 'PDF', icon: FileText },
  { kind: 'DOCX', label: 'DOCX', icon: FileType },
  { kind: 'Excel', label: 'Excel / CSV', icon: FileSpreadsheet },
  { kind: 'PowerPoint', label: 'PowerPoint', icon: Presentation },
  { kind: 'Code', label: 'Code', icon: FileCode2 },
  { kind: 'Image', label: 'Image', icon: ImageIcon },
];

/** Icône d'une pièce jointe selon son type (file_type_for de core/chat_service.py) */
export function attachmentIcon(type: string): LucideIcon {
  return ATTACH_ENTRIES.find((entry) => entry.kind === type)?.icon ?? Paperclip;
}
