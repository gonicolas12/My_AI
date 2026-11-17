/*
 * Ce que l'onglet Documents met en mémoire : fichiers choisis (« Ajouter ») ou
 * déposés, dossiers déposés. Deux fichiers du même nom peuvent y rester, leur
 * date les distingue : quand un fichier ou un dossier remis porte le nom d'un
 * autre déjà en mémoire, le panneau demande quoi faire (stores/memory.ts,
 * askUpdate) : le mettre à jour (il remplace le plus récent du même nom),
 * garder les deux, ou ne pas l'envoyer. Le serveur lit ensuite chaque fichier
 * en arrière-plan, un à la fois (interfaces/desktop/memory.py).
 */

import { t } from '../../../i18n';
import { type AddedDocuments, ApiError, api } from '../../../lib/api';
import { notify } from '../../../stores/app';
import { askUpdate, type UpdateChoice } from '../../../stores/memory';
import { FOLDER_FILES_MAX, readFolder } from './folders';

const errorText = (error: unknown) => (error instanceof ApiError ? error.message : String(error));

/** Nom d'un fichier choisi par son chemin : « C:\docs\rapport.pdf » → « rapport.pdf » */
export const baseName = (path: string): string => path.split(/[\\/]/).pop() || path;

export interface Additions {
  /** Fichiers choisis dans le dialogue du système, par leur chemin */
  paths?: string[];
  /** Fichiers déposés, ou choisis dans un navigateur, par leur contenu */
  files?: File[];
  /** Dossiers déposés, parcourus s'ils partent */
  folders?: FileSystemDirectoryEntry[];
}

/** Envoi au serveur ; un fichier refusé (introuvable, format) s'affiche */
async function send(call: () => Promise<AddedDocuments>): Promise<void> {
  try {
    const { refused } = await call();
    for (const item of refused) notify('error', item.message);
  } catch (error) {
    notify('error', errorText(error));
  }
}

/**
 * Dossier déposé : parcouru, puis ses fichiers envoyés ensemble ; trop gros ou
 * vide, il le dit. target : le dossier déjà en mémoire qu'il met à jour
 */
async function sendFolder(entry: FileSystemDirectoryEntry, target?: string): Promise<void> {
  try {
    const read = await readFolder(entry);
    if (read.tooBig) {
      notify(
        'error',
        t('memory.documents.folderTooBig', { name: read.name, max: FOLDER_FILES_MAX }),
      );
      return;
    }
    if (!read.files.length) {
      notify('info', t('memory.documents.folderEmpty', { name: read.name }));
      return;
    }
    if (read.skipped) {
      notify('info', t('memory.documents.folderSkipped', { name: read.name, count: read.skipped }));
    }
    await send(() => api.uploadMemoryFolder(read.name, read.files, target));
  } catch (error) {
    notify('error', errorText(error));
  }
}

/**
 * Met en mémoire des fichiers et des dossiers. Pour ceux qui portent le nom
 * d'un document, ou d'un dossier, déjà en mémoire, l'utilisateur choisit : les
 * mettre à jour, garder les deux, ou ne pas les envoyer. Les autres partent.
 */
export async function addToMemory({ paths = [], files = [], folders = [] }: Additions) {
  const names = [...paths.map(baseName), ...files.map((file) => file.name)];
  const folderNames = folders.map((folder) => folder.name);
  if (!names.length && !folderNames.length) return;
  let choice: UpdateChoice = 'keep';
  let fileTargets = new Map<string, string>();
  let folderTargets = new Map<string, string>();
  try {
    const existing = await api.existingMemoryDocuments(names, folderNames);
    fileTargets = new Map(existing.files.map((item) => [baseName(item.name), item.target]));
    folderTargets = new Map(existing.folders.map((item) => [item.name, item.target]));
    if (fileTargets.size || folderTargets.size) choice = await askUpdate(existing);
  } catch (error) {
    notify('error', errorText(error));
    return;
  }
  // Déjà là : « Annuler » ne l'envoie pas ; « Mettre à jour » lui donne sa cible
  const sent = (name: string, targets: Map<string, string>) =>
    choice !== 'cancel' || !targets.has(name);
  const target = (name: string, targets: Map<string, string>) =>
    choice === 'update' ? targets.get(name) : undefined;

  const sentPaths = paths.filter((path) => sent(baseName(path), fileTargets));
  if (sentPaths.length) {
    const targets: Record<string, string> = {};
    for (const path of sentPaths) {
      const replaced = target(baseName(path), fileTargets);
      if (replaced) targets[baseName(path)] = replaced;
    }
    await send(() => api.addMemoryDocuments(sentPaths, targets));
  }
  for (const file of files) {
    if (sent(file.name, fileTargets)) {
      await send(() => api.uploadMemoryDocument(file, file.name, target(file.name, fileTargets)));
    }
  }
  for (const folder of folders) {
    if (sent(folder.name, folderTargets)) {
      await sendFolder(folder, target(folder.name, folderTargets));
    }
  }
}
