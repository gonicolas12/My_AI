/*
 * Règles du graphe du workflow (WorkflowCanvas de Tk), sans React Flow.
 *
 * Un lien part du port de sortie d'un nœud vers le port d'entrée d'un autre ;
 * Tk refusait le lien d'un nœud vers lui-même, un doublon et l'aller-retour
 * (A→B puis B→A). Un cycle plus long (A→B→C→A) n'était pas refusé, mais ses
 * nœuds ne s'exécutaient jamais (tri topologique) : il est refusé aussi.
 */

/** Taille d'un nœud du canvas (260 × 110 dans Tk, plus compact ici) */
export const NODE_W = 240;
export const NODE_H = 84;
/** Pas de la grille et de l'aimantation (GRID_SIZE de Tk) */
export const GRID = 25;
/** Zoom de 0,3 à 3, comme Tk */
export const MIN_ZOOM = 0.3;
export const MAX_ZOOM = 3;

export interface Link {
  from: number;
  to: number;
}

export function snap(value: number): number {
  return Math.round(value / GRID) * GRID;
}

/** Placement automatique en cascade (add_node de Tk), quatre nœuds par ligne */
export function autoPosition(count: number): { x: number; y: number } {
  return { x: snap(75 + (count % 4) * 300), y: snap(50 + Math.floor(count / 4) * 125) };
}

/** Un chemin mène-t-il de `start` à `goal` en suivant les liens ? */
function reaches(links: Link[], start: number, goal: number): boolean {
  const next = new Map<number, number[]>();
  for (const link of links) next.set(link.from, [...(next.get(link.from) ?? []), link.to]);
  const seen = new Set<number>();
  const stack = [start];
  while (stack.length) {
    const node = stack.pop() as number;
    if (node === goal) return true;
    if (seen.has(node)) continue;
    seen.add(node);
    stack.push(...(next.get(node) ?? []));
  }
  return false;
}

/** Lien accepté : ni boucle, ni doublon, ni aller-retour, ni cycle */
export function canLink(links: Link[], from: number, to: number): boolean {
  if (from === to) return false;
  if (links.some((link) => link.from === from && link.to === to)) return false;
  return !reaches(links, to, from);
}

/** Liens valides d'un workflow chargé : extrémités connues, sans doublon ni cycle */
export function validLinks(links: Link[], nodeIds: Set<number>): Link[] {
  const kept: Link[] = [];
  for (const link of links) {
    if (!nodeIds.has(link.from) || !nodeIds.has(link.to)) continue;
    if (canLink(kept, link.from, link.to)) kept.push({ from: link.from, to: link.to });
  }
  return kept;
}
