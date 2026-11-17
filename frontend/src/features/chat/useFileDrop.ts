/*
 * Glisser-déposer de fichiers sur la page Chat (on_file_drop de Tk), sur la
 * page Code, qui fournit ses propres pièces jointes, et sur le panneau Mémoire.
 *
 * Tant que des fichiers survolent la fenêtre, la carte de saisie s'éclaire
 * (bordure orange, comme dans Tk). Déposés sur la page, ils deviennent des
 * pièces jointes : par leur vrai chemin dans la fenêtre pywebview (événement
 * files.dropped), par leur contenu dans un navigateur.
 *
 * Une zone sans onPaths (Mémoire) n'a besoin que du contenu : elle le lit dans
 * la page, fenêtre de l'appli comprise. Un fichier sans vrai chemin (glissé
 * depuis Outlook, une archive ZIP ouverte dans l'Explorateur…) n'a pas de
 * files.dropped : par son chemin, il ne donnait rien. Avec onFolders, elle
 * reçoit aussi les dossiers déposés, à parcourir dans la page.
 */

import { useEffect } from 'react';

import { type DropZone, hasFiles, noteDrop, onDroppedPaths } from '../../lib/drops';
import { shell } from '../../lib/shell';
import { setDropping } from '../../stores/composer';
import { attachPaths, droppedFiles, droppedItems, uploadFiles } from './attach';

/** Ce que deviennent les fichiers déposés ; un objet stable (constante de module) */
export interface DropTarget {
  /**
   * Fichiers déposés dans la fenêtre de l'appli, par leur chemin ; sans lui,
   * leur contenu (onFiles), comme dans un navigateur
   */
  onPaths?: (paths: string[]) => void;
  /** Fichiers déposés par leur contenu (navigateur, ou zone sans onPaths) */
  onFiles: (files: File[]) => void;
  /**
   * Dossiers déposés, avec les fichiers déposés en même temps, parcourus dans
   * la page (zone sans onPaths) ; sans lui, un message dit qu'un dossier ne se
   * joint pas ainsi
   */
  onFolders?: (folders: FileSystemDirectoryEntry[], files: File[]) => void;
  /** Des fichiers survolent la fenêtre : la carte de saisie s'éclaire */
  setDropping: (dropping: boolean) => void;
}

const CHAT_TARGET: DropTarget = {
  onPaths: (paths) => void attachPaths(paths),
  onFiles: (files) => void uploadFiles(files),
  setDropping,
};

export function useFileDrop(zone: DropZone, target: DropTarget = CHAT_TARGET) {
  const { onPaths, onFiles, onFolders, setDropping: light } = target;
  // Survol de la fenêtre : entrées et sorties comptées, chaque élément en émet
  useEffect(() => {
    let depth = 0;
    const enter = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      depth += 1;
      light(true);
    };
    const leave = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      depth = Math.max(0, depth - 1);
      if (!depth) light(false);
    };
    const end = () => {
      depth = 0;
      light(false);
    };
    window.addEventListener('dragenter', enter);
    window.addEventListener('dragleave', leave);
    window.addEventListener('drop', end, true);
    window.addEventListener('dragend', end);
    return () => {
      window.removeEventListener('dragenter', enter);
      window.removeEventListener('dragleave', leave);
      window.removeEventListener('drop', end, true);
      window.removeEventListener('dragend', end);
      light(false);
    };
  }, [light]);

  useEffect(() => (onPaths ? onDroppedPaths(zone, onPaths) : undefined), [zone, onPaths]);

  return {
    onDragOver(event: React.DragEvent) {
      if (!hasFiles(event)) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'copy';
    },
    onDrop(event: React.DragEvent) {
      if (!hasFiles(event)) return;
      event.preventDefault();
      // Dans la fenêtre de l'appli, les chemins arrivent ensuite (files.dropped)
      if (onPaths) noteDrop(zone);
      if (onPaths && shell.isDesktop()) return;
      // Navigateur, ou zone qui se contente du contenu : il part au serveur
      if (!onFolders) {
        onFiles(droppedFiles(event.dataTransfer));
        return;
      }
      // Un seul envoi pour le dépôt entier (une seule question « mettre à jour ? »)
      const { files, folders } = droppedItems(event.dataTransfer);
      if (folders.length) onFolders(folders, files);
      else if (files.length) onFiles(files);
    },
  };
}
