/*
 * Glisser-déposer de fichiers sur la fenêtre.
 *
 * Le navigateur ne donne pas le chemin d'un fichier déposé : dans la fenêtre
 * pywebview, le serveur le reçoit de WebView2 et le renvoie par l'événement
 * files.dropped (interfaces/desktop/window.py). La page, elle, sait où le
 * fichier a été déposé : elle le note au moment du dépôt, puis l'événement
 * arrive et la zone choisie reçoit les chemins.
 */

export type DropZone = 'chat' | 'agents';

/** Délai maximal entre le dépôt et l'arrivée des chemins (ms) */
const DROP_WINDOW = 5000;

let lastDrop: { zone: DropZone; at: number } | null = null;
const handlers = new Map<DropZone, (paths: string[]) => void>();

/** Un dépôt vient d'avoir lieu sur cette zone */
export function noteDrop(zone: DropZone): void {
  lastDrop = { zone, at: Date.now() };
}

/** Reçoit les chemins des fichiers déposés sur une zone ; renvoie le désabonnement */
export function onDroppedPaths(zone: DropZone, handler: (paths: string[]) => void): () => void {
  handlers.set(zone, handler);
  return () => {
    if (handlers.get(zone) === handler) handlers.delete(zone);
  };
}

/** Chemins reçus du serveur (files.dropped) : remis à la zone du dernier dépôt */
export function dispatchDroppedPaths(paths: string[]): void {
  const drop = lastDrop;
  lastDrop = null;
  if (!drop || Date.now() - drop.at > DROP_WINDOW) return;
  handlers.get(drop.zone)?.(paths);
}

/** Vrai si l'élément glissé contient des fichiers (et non du texte ou un lien) */
export function hasFiles(event: DragEvent | React.DragEvent): boolean {
  return Array.from(event.dataTransfer?.types ?? []).includes('Files');
}
