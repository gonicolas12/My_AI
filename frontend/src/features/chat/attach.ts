/*
 * Pièces jointes de la zone de saisie : choisies par le menu « + », déposées,
 * ou collées (Ctrl+V). Le serveur les lit en arrière-plan ; l'envoi attend
 * qu'elles soient prêtes (cf. ChatService.add_attachment).
 *
 * Dans la fenêtre pywebview, un fichier se joint par son chemin (dialogue du
 * système, ou chemin d'un dépôt) ; dans un navigateur, son contenu est envoyé
 * au serveur, qui le range dans un dossier temporaire.
 */

import { type MessageKey, t } from '../../i18n';
import { api } from '../../lib/api';
import type { AttachKind } from '../../lib/shell';
import { notify } from '../../stores/app';

/** Extensions de chaque entrée du menu, pour le sélecteur du navigateur */
export const ACCEPT: Record<AttachKind, string> = {
  PDF: '.pdf',
  DOCX: '.docx,.doc',
  Excel: '.xlsx,.xls,.csv',
  PowerPoint: '.pptx,.potx',
  Code: [
    '.py,.pyw,.js,.mjs,.cjs,.ts,.tsx,.jsx,.html,.htm,.css,.scss,.sass,.less,.json,.xml',
    '.yaml,.yml,.toml,.ini,.cfg,.conf,.md,.rst,.txt,.log,.sh,.bash,.bat,.cmd,.ps1,.c,.h',
    '.cpp,.hpp,.cs,.java,.kt,.go,.rs,.rb,.php,.lua,.sql,.vue,.svelte,.dart,.swift',
  ].join(','),
  Image: '.png,.jpg,.jpeg,.gif,.bmp,.webp,.tiff,.tif',
};

/** Tous les types à la fois : bouton Ajouter de la Mémoire, dans un navigateur */
export const ACCEPT_ALL = Object.values(ACCEPT).join(',');

/** Nom d'une image collée depuis le presse-papiers (celui de l'interface Tk) */
export const CLIPBOARD_IMAGE = 'clipboard_image.png';

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** Joint des fichiers par leur chemin ; un refus s'affiche, avec son message */
export async function attachPaths(paths: string[], type?: AttachKind): Promise<void> {
  for (const path of paths) {
    try {
      await api.addAttachment(path, type);
    } catch (error) {
      notify('error', errorText(error));
    }
  }
}

/** Joint des fichiers sans chemin (navigateur, presse-papiers) : leur contenu part au serveur */
export async function uploadFiles(files: File[], name?: string): Promise<void> {
  for (const file of files) {
    try {
      await api.uploadAttachment(file, name ?? file.name);
    } catch (error) {
      notify('error', errorText(error));
    }
  }
}

const isDirectory = (entry: FileSystemEntry | null): entry is FileSystemDirectoryEntry =>
  Boolean(entry?.isDirectory);

/**
 * Fichiers et dossiers déposés, à lire pendant l'événement drop : après, la
 * liste du DataTransfer est vide. Un dossier se parcourt ensuite (Mémoire).
 */
export function droppedItems(transfer: DataTransfer): {
  files: File[];
  folders: FileSystemDirectoryEntry[];
} {
  const files: File[] = [];
  const folders: FileSystemDirectoryEntry[] = [];
  for (const item of Array.from(transfer.items)) {
    if (item.kind !== 'file') continue;
    const entry = item.webkitGetAsEntry();
    if (isDirectory(entry)) {
      folders.push(entry);
      continue;
    }
    const file = item.getAsFile();
    if (file) files.push(file);
  }
  return { files, folders };
}

/**
 * Fichiers déposés lus par leur contenu, sans les dossiers : sans chemin, un
 * dossier ne peut pas être joint (dans la fenêtre de l'appli, le chat joint ses
 * fichiers) ; folderNote le dit à l'utilisateur
 */
export function droppedFiles(
  transfer: DataTransfer,
  folderNote: MessageKey = 'chat.attach.folderInWindow',
): File[] {
  const { files, folders } = droppedItems(transfer);
  if (folders.length) {
    notify('info', t(folderNote));
  }
  return files;
}

/** Fichiers du presse-papiers (image copiée, capture d'écran) */
export function clipboardFiles(event: React.ClipboardEvent): File[] {
  return Array.from(event.clipboardData?.files ?? []);
}
