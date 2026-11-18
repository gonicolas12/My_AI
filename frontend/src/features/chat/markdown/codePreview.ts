/*
 * Aperçu d'un bloc de code d'une réponse : un bloc HTML ou SVG rendable (artefact,
 * lib/artifacts.ts) porte un bouton « Aperçu » dans son en-tête, qui ouvre le volet
 * de droite sur lui. La réponse (AssistantMessage) dit, pour le texte d'un bloc,
 * de quoi l'ouvrir ; ailleurs (page Code, aperçu d'un fichier), aucun bouton.
 */

import { createContext } from 'react';

/** Ouvre l'aperçu du bloc dont voici le code, ou null s'il n'en a pas */
export type CodePreviewFinder = (code: string) => (() => void) | null;

export const CodePreview = createContext<CodePreviewFinder | null>(null);
