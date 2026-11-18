/*
 * Fenêtre d'aperçu au premier plan, comme un panneau, un peu plus grande que
 * les Réglages :
 *  - pièces jointes pas encore envoyées (zone de saisie du chat, zone de tâche
 *    des agents, page Code) ; celles d'un message envoyé s'ouvrent dans le
 *    volet de droite, comme un nom de fichier du chat (stores/preview.ts) ;
 *  - tout ce que la page Agents montre, qui n'a pas de volet de droite :
 *    pièces jointes d'un fil, fichiers cités par un agent, blocs HTML et SVG
 *    de ses résultats.
 */

import { create } from 'zustand';

import { type Artifact, fileArtifact } from '../lib/artifacts';
import type { PreviewTab } from './preview';

export interface PreviewFile {
  path: string;
  name: string;
}

interface AttachmentPreviewState {
  open: boolean;
  /** Fichiers ou blocs, dans leur ordre : la fenêtre passe de l'un à l'autre */
  items: Artifact[];
  index: number;
  tab: PreviewTab;
}

export const useAttachmentPreview = create<AttachmentPreviewState>()(() => ({
  open: false,
  items: [],
  index: 0,
  tab: 'preview',
}));

/** Ouvre la fenêtre sur un fichier ou un bloc HTML/SVG, ses voisins à côté (‹ k/n ›) */
export function openPreviewWindow(items: Artifact[], index = 0): void {
  if (!items.length) return;
  useAttachmentPreview.setState({
    open: true,
    items,
    index: Math.min(Math.max(index, 0), items.length - 1),
    tab: 'preview',
  });
}

/** Ouvre la fenêtre sur des pièces jointes (nom affiché : celui de la vignette) */
export function openAttachmentPreview(items: PreviewFile[], index = 0): void {
  openPreviewWindow(
    items.map((item, at) => ({ ...fileArtifact(item.path, false, at), title: item.name })),
    index,
  );
}

/** Fermée : les pièces jointes restent le temps qu'elle s'efface */
export function closeAttachmentPreview(): void {
  useAttachmentPreview.setState({ open: false });
}

export function showAttachmentPreviewItem(index: number): void {
  useAttachmentPreview.setState((state) =>
    index >= 0 && index < state.items.length ? { index, tab: 'preview' } : state,
  );
}

export function setAttachmentPreviewTab(tab: PreviewTab): void {
  useAttachmentPreview.setState({ tab });
}
