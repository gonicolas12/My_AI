/*
 * Volet d'aperçu de droite (artefacts HTML/SVG, documents) : façon Claude
 * Artifacts, comme le volet de l'interface Tk (artifacts_panel.py).
 *
 * Il montre un artefact à la fois parmi ceux d'une réponse ; sa largeur est
 * réglable et retenue d'un lancement à l'autre.
 */

import { create } from 'zustand';

import { savePreviewWidth } from '../lib/actions';
import type { Artifact } from '../lib/artifacts';

export type PreviewTab = 'preview' | 'code';

/** Largeur par défaut et bornes du volet (Tk : 560, de 320 à 1200 px) */
export const PREVIEW_WIDTH = { initial: 560, min: 320, max: 1200 };

interface PreviewState {
  open: boolean;
  /** Réponse d'origine */
  mid: string | null;
  items: Artifact[];
  index: number;
  tab: PreviewTab;
  width: number;
}

export const usePreview = create<PreviewState>()(() => ({
  open: false,
  mid: null,
  items: [],
  index: 0,
  tab: 'preview',
  width: PREVIEW_WIDTH.initial,
}));

export function clampPreviewWidth(width: number): number {
  return Math.round(Math.min(PREVIEW_WIDTH.max, Math.max(PREVIEW_WIDTH.min, width)));
}

/** Ouvre le volet sur un artefact d'une réponse */
export function openPreview(mid: string | null, items: Artifact[], index = 0): void {
  if (!items.length) return;
  usePreview.setState({
    open: true,
    mid,
    items,
    index: Math.min(Math.max(index, 0), items.length - 1),
    tab: 'preview',
  });
}

export function closePreview(): void {
  usePreview.setState({ open: false });
}

export function showPreviewItem(index: number): void {
  usePreview.setState((state) =>
    index >= 0 && index < state.items.length ? { index, tab: 'preview' } : state,
  );
}

export function setPreviewTab(tab: PreviewTab): void {
  usePreview.setState({ tab });
}

/** Largeur du volet (glisser la poignée) ; `persist` la retient pour le prochain lancement */
export function setPreviewWidth(width: number, persist = false): void {
  const clamped = clampPreviewWidth(width);
  usePreview.setState({ width: clamped });
  if (persist) savePreviewWidth(clamped);
}
