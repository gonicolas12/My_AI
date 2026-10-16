/*
 * Passage à surligner après l'ouverture d'un résultat de la recherche globale
 * (_highlight_in_chat de Tk) : le fil le trouve, le fait défiler à l'écran
 * puis le surligne ; un clic dans le fil efface le surlignage.
 */

import { create } from 'zustand';

export interface HighlightTarget {
  conversationId: string;
  /** Texte indexé du message trouvé */
  excerpt: string;
  /** Requête de la recherche : ses mots sont surlignés */
  query: string;
  /** Position du message dans la session enregistrée (repli) */
  messageIndex: number;
}

export const useHighlight = create<{ target: HighlightTarget | null }>()(() => ({
  target: null,
}));

export function requestHighlight(target: HighlightTarget): void {
  useHighlight.setState({ target });
}

export function clearHighlightTarget(): void {
  useHighlight.setState({ target: null });
}
