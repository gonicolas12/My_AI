/* Icône d'un fichier selon son format (en-têtes des aperçus) */

import {
  File,
  FileCode2,
  FileImage,
  FileSpreadsheet,
  FileText,
  FileVideo,
  type LucideIcon,
  Music,
  Presentation,
} from 'lucide-react';

import { extensionOf } from '../../lib/artifacts';
import { type FileKind, fileKind } from '../../lib/fileKinds';

const KIND_ICONS: Partial<Record<FileKind, LucideIcon>> = {
  image: FileImage,
  svg: FileImage,
  video: FileVideo,
  audio: Music,
  pdf: FileText,
  table: FileSpreadsheet,
  markdown: FileText,
  html: FileCode2,
  code: FileCode2,
  text: FileText,
};

export function fileIcon(path: string): LucideIcon {
  const kind = fileKind(path);
  if (kind === 'office') {
    const extension = extensionOf(path);
    if (['.xlsx', '.xlsm', '.xls'].includes(extension)) return FileSpreadsheet;
    if (['.pptx', '.potx', '.ppt'].includes(extension)) return Presentation;
    return FileText;
  }
  return KIND_ICONS[kind] ?? File;
}
