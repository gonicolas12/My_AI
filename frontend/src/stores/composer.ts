import { create } from 'zustand';

/** Brouillon de la zone de saisie : il survit au passage accueil → fil et aux onglets */
interface ComposerState {
  draft: string;
}

export const useComposer = create<ComposerState>()(() => ({ draft: '' }));

export function setDraft(draft: string): void {
  useComposer.setState({ draft });
}
