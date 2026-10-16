/*
 * Palette de commandes (Ctrl+K) : ouverte ou fermée. Ouverte, elle prend le
 * clavier : les autres raccourcis de la fenêtre attendent sa fermeture, comme
 * dans Tk où la palette est une fenêtre à part.
 */

import { create } from 'zustand';

export const usePalette = create<{ open: boolean }>()(() => ({ open: false }));

export function togglePalette(): void {
  usePalette.setState((state) => ({ open: !state.open }));
}

export function closePalette(): void {
  usePalette.setState({ open: false });
}
