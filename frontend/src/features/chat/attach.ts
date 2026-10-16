/*
 * Pièces jointes de la zone de saisie : choisies par le menu « + », déposées,
 * ou collées (Ctrl+V). Le serveur les lit en arrière-plan ; l'envoi attend
 * qu'elles soient prêtes (cf. ChatService.add_attachment).
 *
 * Dans la fenêtre pywebview, un fichier se joint par son chemin (dialogue du
 * système, ou chemin d'un dépôt) ; dans un navigateur, son contenu est envoyé
 * au serveur, qui le range dans un dossier temporaire.
 */

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

/**
 * Fichiers déposés dans un navigateur, sans les dossiers : sans chemin, un
 * dossier ne peut pas être lu (dans la fenêtre de l'appli, il joint ses fichiers)
 */
export function droppedFiles(transfer: DataTransfer): File[] {
  const items = Array.from(transfer.items).filter((item) => item.kind === 'file');
  const isFolder = (item: DataTransferItem) => Boolean(item.webkitGetAsEntry()?.isDirectory);
  if (items.some(isFolder)) {
    notify('info', '📁 Un dossier se joint en le glissant dans la fenêtre de l’appli');
  }
  return items
    .filter((item) => !isFolder(item))
    .map((item) => item.getAsFile())
    .filter((file): file is File => file !== null);
}

/** Fichiers du presse-papiers (image copiée, capture d'écran) */
export function clipboardFiles(event: React.ClipboardEvent): File[] {
  return Array.from(event.clipboardData?.files ?? []);
}
