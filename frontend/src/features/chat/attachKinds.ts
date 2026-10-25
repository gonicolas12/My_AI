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

import type { MessageKey } from '../../i18n';
import type { AttachKind } from '../../lib/shell';

export const ATTACH_ENTRIES: { kind: AttachKind; label: MessageKey; icon: LucideIcon }[] = [
  { kind: 'PDF', label: 'chat.attach.kind.pdf', icon: FileText },
  { kind: 'DOCX', label: 'chat.attach.kind.docx', icon: FileType },
  { kind: 'Excel', label: 'chat.attach.kind.excel', icon: FileSpreadsheet },
  { kind: 'PowerPoint', label: 'chat.attach.kind.powerpoint', icon: Presentation },
  { kind: 'Code', label: 'chat.attach.kind.code', icon: FileCode2 },
  { kind: 'Image', label: 'chat.attach.kind.image', icon: ImageIcon },
];

/** Icône d'une pièce jointe selon son type (file_type_for de core/chat_service.py) */
export function attachmentIcon(type: string): LucideIcon {
  return ATTACH_ENTRIES.find((entry) => entry.kind === type)?.icon ?? Paperclip;
}
