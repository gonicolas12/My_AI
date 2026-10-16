import { create } from 'zustand';

/** Brouillon de la zone de saisie : il survit au passage accueil → fil et aux onglets */
interface ComposerState {
  draft: string;
  /** Des fichiers sont glissés au-dessus de la page : la carte de saisie s'éclaire */
  dropping: boolean;
}

export const useComposer = create<ComposerState>()(() => ({ draft: '', dropping: false }));

export function setDraft(draft: string): void {
  useComposer.setState({ draft });
}

export function setDropping(dropping: boolean): void {
  if (useComposer.getState().dropping !== dropping) useComposer.setState({ dropping });
}
