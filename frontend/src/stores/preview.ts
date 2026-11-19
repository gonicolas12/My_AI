/*
 * Volet d'aperçu de droite (artefacts HTML/SVG, documents, fichiers) : façon
 * Claude Artifacts, comme le volet de l'interface Tk (artifacts_panel.py).
 *
 * Il montre un artefact à la fois parmi ceux d'une réponse, ou un fichier
 * cliqué dans le chat (nom cité, carte, image, pièce jointe d'un message
 * envoyé) ; sa largeur est réglable et retenue d'un lancement à l'autre. Il
 * s'ouvre et se ferme en douceur : fermé, il reste affiché le temps de se
 * replier (closing).
 *
 * Le chat et la page Code ont chacun le leur (page) : un volet ouvert dans
 * l'une ne paraît pas dans l'autre, et la retrouve en revenant. Il n'y en a
 * qu'un à la fois : en ouvrir un dans une page ferme celui de l'autre.
 */

import { create } from 'zustand';

import { savePreviewWidth } from '../lib/actions';
import { type Artifact, fileArtifact } from '../lib/artifacts';
import { type Tab, useApp } from './app';

export type PreviewTab = 'preview' | 'code';

/** Largeur par défaut et bornes du volet (Tk : 560, de 320 à 1200 px) */
export const PREVIEW_WIDTH = { initial: 560, min: 320, max: 1200 };

/** Ouverture et fermeture d'un volet d'aperçu (--motion-pane de tokens.css) */
export const PANE_MS = 240;

/** Durée d'une animation, nulle en mouvement réduit (tokens.css la coupe aussi) */
export function motionMs(ms: number): number {
  const reduced =
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  return reduced ? 0 : ms;
}

interface PreviewState {
  open: boolean;
  /** Fermé, il se replie encore (PANE_MS) */
  closing: boolean;
  /** Page qui le montre (celle d'où il a été ouvert) */
  page: Tab;
  /** Réponse d'origine */
  mid: string | null;
  items: Artifact[];
  index: number;
  tab: PreviewTab;
  width: number;
}

export const usePreview = create<PreviewState>()(() => ({
  open: false,
  closing: false,
  page: 'chat',
  mid: null,
  items: [],
  index: 0,
  tab: 'preview',
  width: PREVIEW_WIDTH.initial,
}));

let closeTimer: ReturnType<typeof setTimeout> | null = null;

function cancelClose(): void {
  if (closeTimer) clearTimeout(closeTimer);
  closeTimer = null;
}

export function clampPreviewWidth(width: number): number {
  return Math.round(Math.min(PREVIEW_WIDTH.max, Math.max(PREVIEW_WIDTH.min, width)));
}

/**
 * Ouvre le volet sur un artefact d'une réponse
 *
 * @param page page qui le montre : celle affichée, sauf ouverture différée (fin d'une réponse)
 */
export function openPreview(
  mid: string | null,
  items: Artifact[],
  index = 0,
  page: Tab = useApp.getState().tab,
): void {
  if (!items.length) return;
  cancelClose();
  usePreview.setState({
    open: true,
    closing: false,
    page,
    mid,
    items,
    index: Math.min(Math.max(index, 0), items.length - 1),
    tab: 'preview',
  });
}

/**
 * Ouvre le volet sur un fichier cliqué dans le chat (nom cité, carte, image,
 * pièce jointe d'un message envoyé)
 *
 * @param generated produit par l'appli : il s'ouvre aussi dans son application
 */
export function openFilePreview(path: string, generated = false, mid: string | null = null): void {
  if (!path) return;
  openPreview(mid, [fileArtifact(path, generated)]);
}

/** Ferme le volet s'il est celui de cette page (conversation changée ou effacée) */
export function closePagePreview(page: Tab): void {
  if (usePreview.getState().page === page) closePreview();
}

export function closePreview(): void {
  const state = usePreview.getState();
  if (!state.open || state.closing) return;
  const delay = motionMs(PANE_MS);
  if (!delay) {
    usePreview.setState({ open: false });
    return;
  }
  usePreview.setState({ closing: true });
  cancelClose();
  closeTimer = setTimeout(() => {
    closeTimer = null;
    usePreview.setState({ open: false, closing: false });
  }, delay);
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
