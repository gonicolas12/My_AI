/*
 * Liens ajoutés au rendu d'une réponse, comme l'interface Tk à la fin du
 * streaming :
 *  - citations numérotées « [n] » de la recherche web, ouvertes dans le
 *    navigateur du système (_apply_inline_citations, utils/citations.py) ;
 *  - chemins de fichiers et de dossiers existants, montrés dans l'Explorateur
 *    (_linkify_file_paths). Le serveur les repère, car lui seul voit le
 *    disque ; jamais dans un bloc de code.
 *
 * Greffon rehype : il découpe les nœuds de texte et y insère des éléments
 * propres à l'appli (« chat-cite », « chat-path »), rendus par Markdown.tsx.
 */

import type { PathLink } from '../../../lib/events';

/** Bloc « Sources » : « [n] [label](url) » ou « [n] url » (parse_citation_map) */
const CITATION_SOURCE = /\[(\d{1,3})\]\s*(?:\[[^\]]*\]\()?(https?:\/\/[^)\s]+)/g;

function cleanUrl(url: string): string {
  return url.replace(/[.,;:) ]+$/, '');
}

/** Table n → url tirée du bloc de sources numérotées d'une réponse */
export function parseCitationMap(text: string): Map<number, string> {
  const map = new Map<number, string>();
  for (const match of (text ?? '').matchAll(CITATION_SOURCE)) {
    const n = Number(match[1]);
    if (!map.has(n) && match[2]) map.set(n, cleanUrl(match[2]));
  }
  return map;
}

/** Clé stable d'une table de citations (pour ne re-rendre qu'à son changement) */
export function citationKey(text: string): string {
  if (!text || !text.includes('http')) return '';
  return [...parseCitationMap(text)].map(([n, url]) => `${n}=${url}`).join('\n');
}

export interface ChatLinks {
  citations: Map<number, string>;
  paths: PathLink[];
}

export function buildChatLinks(key: string, paths: PathLink[] | undefined): ChatLinks | null {
  const citations = new Map<number, string>();
  for (const line of key ? key.split('\n') : []) {
    const at = line.indexOf('=');
    citations.set(Number(line.slice(0, at)), line.slice(at + 1));
  }
  if (!citations.size && !paths?.length) return null;
  return { citations, paths: paths ?? [] };
}

/** Nœud hast (texte, élément, racine…), réduit à ce que le greffon lit */
interface HastNode {
  type: string;
  value?: string;
  tagName?: string;
  properties?: Record<string, unknown>;
  children?: HastNode[];
}

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function element(tagName: string, properties: Record<string, unknown>, text: string): HastNode {
  return { type: 'element', tagName, properties, children: [{ type: 'text', value: text }] };
}

/** Découpe un texte autour des citations et des chemins connus */
function splitText(
  value: string,
  links: ChatLinks,
  pattern: RegExp,
  pathsByText: Map<string, string>,
  inCode: boolean,
): HastNode[] | null {
  const out: HastNode[] = [];
  let cursor = 0;
  pattern.lastIndex = 0;
  for (const match of value.matchAll(pattern)) {
    const at = match.index;
    let node: HastNode | null = null;
    if (match[1] !== undefined) {
      // Citation « [n] » : jamais dans du code
      const url = inCode ? undefined : links.citations.get(Number(match[1]));
      if (url) node = element('chat-cite', { href: url, n: match[1] }, match[0]);
    } else {
      const path = pathsByText.get(match[0]);
      if (path) node = element('chat-path', { path }, match[0]);
    }
    if (!node) continue;
    if (at > cursor) out.push({ type: 'text', value: value.slice(cursor, at) });
    out.push(node);
    cursor = at + match[0].length;
  }
  if (!out.length) return null;
  if (cursor < value.length) out.push({ type: 'text', value: value.slice(cursor) });
  return out;
}

function transform(
  node: HastNode,
  links: ChatLinks,
  pattern: RegExp,
  pathsByText: Map<string, string>,
  inCode: boolean,
): void {
  const children = node.children;
  if (!children) return;
  const next: HastNode[] = [];
  for (const child of children) {
    if (child.type === 'text') {
      const parts = splitText(child.value ?? '', links, pattern, pathsByText, inCode);
      if (parts) next.push(...parts);
      else next.push(child);
      continue;
    }
    if (child.type === 'element') {
      const tag = child.tagName;
      // Bloc de code (pre) et liens existants : laissés tels quels
      if (tag !== 'pre' && tag !== 'a') {
        transform(child, links, pattern, pathsByText, inCode || tag === 'code');
      }
    } else {
      transform(child, links, pattern, pathsByText, inCode);
    }
    next.push(child);
  }
  node.children = next;
}

/** Greffon rehype : citations et chemins cliquables */
export function rehypeChatLinks(links: ChatLinks) {
  const pathsByText = new Map(links.paths.map((item) => [item.text, item.path]));
  // Chemins du plus long au plus court : « C:\a\b.txt » avant « C:\a »
  const alternatives = [...pathsByText.keys()]
    .sort((a, b) => b.length - a.length)
    .map(escapeRegExp);
  const source = alternatives.length
    ? `\\[(\\d{1,3})\\]|${alternatives.join('|')}`
    : '\\[(\\d{1,3})\\]';
  return () => (tree: HastNode) => {
    transform(tree, links, new RegExp(source, 'g'), pathsByText, false);
  };
}
