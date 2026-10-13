/*
 * Surlignage d'un passage trouvé par la recherche globale (_highlight_in_chat
 * et _find_result_widget de Tk) :
 *  - le message se retrouve par son texte (l'extrait indexé est le message
 *    entier), à défaut par sa position dans la session ;
 *  - les mots de la requête y sont surlignés (la requête entière d'abord) ;
 *    s'il n'en contient aucun littéralement (recherche sémantique), tout le
 *    message l'est.
 *
 * Le surlignage passe par l'API CSS Custom Highlight : le DOM rendu par React
 * n'est pas modifié.
 */

import type { MessageView } from './events';

const HIGHLIGHT_NAME = 'search-hit';
const WHOLE_MESSAGE_CLASS = 'search-hit-message';

function normalize(text: string): string {
  return text.toLowerCase().split(/\s+/).filter(Boolean).join(' ');
}

/** Index du message correspondant à un résultat de recherche, ou -1 */
export function findResultMessage(
  messages: MessageView[],
  excerpt: string,
  messageIndex: number,
): number {
  const needle = normalize(excerpt);
  if (!needle) return -1;
  const exact = messages.findIndex((message) => normalize(message.text) === needle);
  if (exact >= 0) return exact;
  // Début de l'extrait présent (texte réécrit depuis l'indexation)
  const head = needle.slice(0, 60);
  const partial = messages.findIndex((message) => normalize(message.text).includes(head));
  if (partial >= 0) return partial;
  return messageIndex >= 0 && messageIndex < messages.length ? messageIndex : -1;
}

/** Mots à surligner : la requête entière, puis ses mots d'au moins 2 lettres */
export function highlightTokens(query: string): string[] {
  const words = query.split(/\s+/).filter((word) => word.length >= 2);
  const whole = query.trim();
  return [...new Set(whole ? [whole, ...words] : words)];
}

interface HighlightRegistry {
  set(name: string, highlight: unknown): void;
  delete(name: string): void;
}

function registry(): HighlightRegistry | null {
  const css = (globalThis as { CSS?: { highlights?: HighlightRegistry } }).CSS;
  return css?.highlights ?? null;
}

let marked: HTMLElement | null = null;

/** Efface le surlignage en place */
export function clearHighlight(): void {
  registry()?.delete(HIGHLIGHT_NAME);
  marked?.classList.remove(WHOLE_MESSAGE_CLASS);
  marked = null;
}

/** Surligne les mots de la requête dans l'élément ; tout l'élément s'il n'en contient aucun */
export function highlightElement(element: HTMLElement, query: string): void {
  clearHighlight();
  const highlights = registry();
  const HighlightClass = (globalThis as { Highlight?: new (...ranges: Range[]) => unknown })
    .Highlight;
  const ranges: Range[] = [];
  if (highlights && HighlightClass) {
    const walker = document.createTreeWalker(element, NodeFilter.SHOW_TEXT);
    const nodes: Text[] = [];
    for (let node = walker.nextNode(); node; node = walker.nextNode()) nodes.push(node as Text);
    for (const token of highlightTokens(query)) {
      const needle = token.toLowerCase();
      for (const node of nodes) {
        const haystack = (node.data ?? '').toLowerCase();
        let at = haystack.indexOf(needle);
        while (at >= 0) {
          const range = document.createRange();
          range.setStart(node, at);
          range.setEnd(node, at + needle.length);
          ranges.push(range);
          at = haystack.indexOf(needle, at + needle.length);
        }
      }
    }
  }
  if (ranges.length && highlights && HighlightClass) {
    highlights.set(HIGHLIGHT_NAME, new HighlightClass(...ranges));
    return;
  }
  element.classList.add(WHOLE_MESSAGE_CLASS);
  marked = element;
}
