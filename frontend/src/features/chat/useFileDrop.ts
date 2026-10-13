/*
 * Glisser-déposer de fichiers sur la page Chat (on_file_drop de Tk).
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
import { attachPaths, uploadFiles } from './attach';

export function useFileDrop(zone: DropZone) {
  // Survol de la fenêtre : entrées et sorties comptées, chaque élément en émet
  useEffect(() => {
    let depth = 0;
    const enter = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      depth += 1;
      setDropping(true);
    };
    const leave = (event: DragEvent) => {
      if (!hasFiles(event)) return;
      depth = Math.max(0, depth - 1);
      if (!depth) setDropping(false);
    };
    const end = () => {
      depth = 0;
      setDropping(false);
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
      setDropping(false);
    };
  }, []);

  useEffect(() => onDroppedPaths(zone, (paths) => void attachPaths(paths)), [zone]);

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
      if (!shell.isDesktop()) void uploadFiles(Array.from(event.dataTransfer.files));
    },
  };
}
