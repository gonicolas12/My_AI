/*
 * Worker de coloration du code : Shiki compile ses grammaires et colore ici,
 * hors du fil de la fenêtre (cf. highlightCore.ts).
 */

import { highlightCode } from './highlightCore';
import type { CodeToken } from './languages';

export interface HighlightRequest {
  id: number;
  code: string;
  lang: string | undefined;
}

export interface HighlightResponse {
  id: number;
  tokens: CodeToken[][] | null;
}

const scope = self as unknown as {
  onmessage: ((event: MessageEvent<HighlightRequest>) => void) | null;
  postMessage: (message: HighlightResponse) => void;
};

scope.onmessage = (event) => {
  const { id, code, lang } = event.data;
  highlightCode(code, lang).then(
    (tokens) => scope.postMessage({ id, tokens }),
    () => scope.postMessage({ id, tokens: null }),
  );
};
