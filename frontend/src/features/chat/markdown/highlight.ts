/*
 * Coloration du code, déléguée au worker de coloration : la fenêtre envoie le
 * code et reçoit les jetons colorés, sans jamais attendre Shiki. Sans worker
 * (tests), le code reste en texte brut.
 */

import type { HighlightRequest, HighlightResponse } from './highlight.worker';
import { type CodeToken, resolveLanguage } from './languages';

export { resolveLanguage } from './languages';
export type { CodeToken } from './languages';

let worker: Worker | null | undefined;
let nextId = 1;
const waiting = new Map<number, (tokens: CodeToken[][] | null) => void>();

function failAll(): void {
  for (const resolve of waiting.values()) resolve(null);
  waiting.clear();
}

function getWorker(): Worker | null {
  if (worker !== undefined) return worker;
  if (typeof Worker === 'undefined') {
    worker = null;
    return worker;
  }
  try {
    worker = new Worker(new URL('./highlight.worker.ts', import.meta.url), { type: 'module' });
  } catch {
    worker = null;
    return worker;
  }
  worker.onmessage = (event: MessageEvent<HighlightResponse>) => {
    const resolve = waiting.get(event.data.id);
    waiting.delete(event.data.id);
    resolve?.(event.data.tokens);
  };
  worker.onerror = () => {
    // Worker en échec : le code reste en texte brut
    failAll();
    worker?.terminate();
    worker = null;
  };
  return worker;
}

/** Jetons colorés du code, ligne par ligne ; null si le langage est inconnu */
export function highlightCode(
  code: string,
  lang: string | undefined,
): Promise<CodeToken[][] | null> {
  if (!resolveLanguage(lang)) return Promise.resolve(null);
  const target = getWorker();
  if (!target) return Promise.resolve(null);
  return new Promise((resolve) => {
    const id = nextId++;
    waiting.set(id, resolve);
    const request: HighlightRequest = { id, code, lang };
    target.postMessage(request);
  });
}
