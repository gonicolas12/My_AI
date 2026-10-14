/*
 * Panneaux de la fenêtre : Réglages, Mémoire, Prompts, Relay, Aide. Ce sont
 * des dialogues internes (jamais une seconde fenêtre), un seul à la fois.
 */

import { create } from 'zustand';

export type PanelId = 'settings' | 'memory' | 'prompts' | 'relay' | 'help';

interface PanelsState {
  open: PanelId | null;
}

export const usePanels = create<PanelsState>()(() => ({ open: null }));

export function openPanel(id: PanelId): void {
  usePanels.setState({ open: id });
}

export function closePanel(): void {
  usePanels.setState({ open: null });
}

/** Ouvre le panneau, ou le ferme s'il est déjà ouvert (raccourcis) */
export function togglePanel(id: PanelId): void {
  usePanels.setState((state) => ({ open: state.open === id ? null : id }));
}
