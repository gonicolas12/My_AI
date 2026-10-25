/*
 * Texte traduit qui contient des éléments : « installez-le depuis
 * <link>ollama.com</link> puis Réessayez ». Chaque balise du catalogue
 * (simple, sans imbrication) est rendue par la fonction de même nom ; l'ordre
 * des mots reste celui de chaque langue.
 */

import { Fragment, type ReactNode } from 'react';

import { type MessageKey, type Params, useT } from './index';

const TAG = /<(\w+)>(.*?)<\/\1>/g;

interface TransProps {
  k: MessageKey;
  params?: Params;
  components: Readonly<Record<string, (chunk: string) => ReactNode>>;
}

export function Trans({ k, params, components }: TransProps) {
  const t = useT();
  const text = t(k, params);
  const parts: ReactNode[] = [];
  let last = 0;
  for (const match of text.matchAll(TAG)) {
    const [whole, name = '', chunk = ''] = match;
    if (match.index > last) parts.push(text.slice(last, match.index));
    const renderChunk = components[name];
    parts.push(<Fragment key={match.index}>{renderChunk ? renderChunk(chunk) : chunk}</Fragment>);
    last = match.index + whole.length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <>{parts}</>;
}
