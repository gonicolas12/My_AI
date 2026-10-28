/*
 * Glisser-déposer de fichiers sur la page Chat (on_file_drop de Tk), et sur la
 * page Code, qui fournit ses propres pièces jointes.
 *
 * Tant que des fichiers survolent la fenêtre, la carte de saisie s'éclaire
 * (bordure orange, comme dans Tk). Déposés sur la page, ils deviennent des
 * pièces jointes : par leur vrai chemin dans la fenêtre pywebview (événement
 * files.dropped), par leur contenu dans un navigateur.
 */

import { useEffect } from 'react';

import { type DropZone, hasFiles, noteDrop, onDroppedPaths } from '../../lib/drops';
import { shell } from '../../lib/shell';
import { setDropping } from '../../stores/composer';
import { attachPaths, droppedFiles, uploadFiles } from './attach';

/** Ce que deviennent les fichiers déposés ; un objet stable (constante de module) */
export interface DropTarget {
  /** Fichiers déposés dans la fenêtre de l'appli, par leur chemin */
  onPaths: (paths: string[]) => void;
  /** Fichiers déposés dans un navigateur : leur contenu */
  onFiles: (files: File[]) => void;
  /** Des fichiers survolent la fenêtre : la carte de saisie s'éclaire */
  setDropping: (dropping: boolean) => void;
}

const CHAT_TARGET: DropTarget = {
  onPaths: (paths) => void attachPaths(paths),
  onFiles: (files) => void uploadFiles(files),
  setDropping,
};

export function useFileDrop(zone: DropZone, target: DropTarget = CHAT_TARGET) {
  const { onPaths, onFiles, setDropping: light } = target;
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

  useEffect(() => onDroppedPaths(zone, onPaths), [zone, onPaths]);

  return {
    onDragOver(event: React.DragEvent) {
      if (!hasFiles(event)) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'copy';
    },
    onDrop(event: React.DragEvent) {
      if (!hasFiles(event)) return;
      event.preventDefault();
      noteDrop(zone);
      // Navigateur : pas de chemin, le contenu part au serveur
      if (!shell.isDesktop()) onFiles(droppedFiles(event.dataTransfer));
    },
  };
}
