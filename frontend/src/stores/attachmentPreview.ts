/*
 * Fenêtre d'aperçu des pièces jointes pas encore envoyées (zone de saisie du
 * chat, zone de tâche des agents, page Code) : au premier plan, comme un
 * panneau, un peu plus grande que les Réglages. Celles d'un message envoyé
 * s'ouvrent dans le volet de droite, comme un nom de fichier du chat
 * (stores/preview.ts).
 */

import { create } from 'zustand';

import type { PreviewTab } from './preview';

export interface PreviewFile {
  path: string;
  name: string;
}

interface AttachmentPreviewState {
  open: boolean;
  /** Pièces jointes de la zone de saisie, dans leur ordre : la fenêtre passe de l'une à l'autre */
  items: PreviewFile[];
  index: number;
  tab: PreviewTab;
}

export const useAttachmentPreview = create<AttachmentPreviewState>()(() => ({
  open: false,
  items: [],
  index: 0,
  tab: 'preview',
}));

export function openAttachmentPreview(items: PreviewFile[], index = 0): void {
  if (!items.length) return;
  useAttachmentPreview.setState({
    open: true,
    items,
    index: Math.min(Math.max(index, 0), items.length - 1),
    tab: 'preview',
  });
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
