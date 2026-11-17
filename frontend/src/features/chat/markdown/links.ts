/*
 * Liens ajoutés au rendu d'une réponse, comme l'interface Tk à la fin du
 * streaming :
 *  - citations numérotées « [n] » de la recherche web, ouvertes dans le
 *    navigateur du système (_apply_inline_citations, utils/citations.py) ;
 *  - chemins de fichiers et de dossiers existants, montrés dans l'Explorateur
 *    (_linkify_file_paths). Le serveur les repère, car lui seul voit le
 *    disque ; jamais dans un bloc de code ;
 *  - documents et dossiers de la Mémoire cités, ouverts dans son onglet
 *    Documents. Le serveur les repère aussi (memory_links), lui seul connaît
 *    la mémoire ; un nom courant (« projet ») ne compte que dans du code.
 *
 * Un lien Markdown vers autre chose qu'une page web, que le modèle invente
 * (« [Dossier X](memory://x) », « [rapport](C:\…\rapport.pdf) »), devient un
 * chemin ou un document de la Mémoire quand sa cible ou son texte en désigne
 * un ; sinon il ne garde que son texte.
 *
 * Greffon rehype : il découpe les nœuds de texte et y insère des éléments
 * propres à l'appli (« chat-cite », « chat-path », « chat-memory »), rendus
 * par Markdown.tsx.
 */

import type { MemoryLink, PathLink } from '../../../lib/events';
import { segments } from './math';

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

/** Lien dont la cible contient une espace, hors titre entre guillemets */
const SPACED_LINK = /(\[[^\]\n]*\]\()([^()<>\n"']*\s[^()<>\n"']*)(\))/g;

/**
 * « [Dossier X](memory://one drive) » : une cible avec des espaces n'est pas un
 * lien pour Markdown, qui l'affichait telle quelle. Entre < >, elle en est un.
 * Le code (blocs et `code` en ligne) n'est jamais modifié.
 */
export function prepareLinks(text: string): string {
  if (!text.includes('](')) return text;
  return segments(text)
    .map((segment) =>
      segment.code
        ? segment.value
        : segment.value.replace(SPACED_LINK, (_match, open: string, target: string, close) => {
            const trimmed = target.trim();
            return /\s/.test(trimmed) ? `${open}<${trimmed}>${close}` : `${open}${trimmed}${close}`;
          }),
    )
    .join('');
}

export interface ChatLinks {
  citations: Map<number, string>;
  paths: PathLink[];
  memory: MemoryLink[];
}

export function buildChatLinks(
  key: string,
  paths: PathLink[] | undefined,
  memory?: MemoryLink[],
): ChatLinks | null {
  const citations = new Map<number, string>();
  for (const line of key ? key.split('\n') : []) {
    const at = line.indexOf('=');
    citations.set(Number(line.slice(0, at)), line.slice(at + 1));
  }
  if (!citations.size && !paths?.length && !memory?.length) return null;
  return { citations, paths: paths ?? [], memory: memory ?? [] };
}

/** Nœud hast (texte, élément, racine…), réduit à ce que le greffon lit */
interface HastNode {
  type: string;
  value?: string;
  tagName?: string;
  properties?: Record<string, unknown>;
  children?: HastNode[];
}

/** Ce qu'un texte repéré par le serveur désigne */
type Target = { path: string } | { memory: MemoryLink };

function escapeRegExp(text: string): string {
  return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function element(tagName: string, properties: Record<string, unknown>, text: string): HastNode {
  return { type: 'element', tagName, properties, children: [{ type: 'text', value: text }] };
}

function memoryElement(link: MemoryLink, children: HastNode[]): HastNode {
  return {
    type: 'element',
    tagName: 'chat-memory',
    properties: { kind: link.kind, name: link.name, folder: link.folder ?? '' },
    children,
  };
}

function textOf(node: HastNode): string {
  if (node.type === 'text') return node.value ?? '';
  return (node.children ?? []).map(textOf).join('');
}

/** Découpe un texte autour des citations, des chemins et des noms de la Mémoire */
function splitText(
  value: string,
  links: ChatLinks,
  pattern: RegExp,
  targets: Map<string, Target>,
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
      const target = targets.get(match[0]);
      if (target && 'path' in target) node = element('chat-path', { path: target.path }, match[0]);
      // Nom courant (« projet ») : seulement dans du code, pas au fil du texte
      else if (target && (inCode || !target.memory.strict)) {
        node = memoryElement(target.memory, [{ type: 'text', value: match[0] }]);
      }
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

/** Page web, adresse mail ou ancre : un vrai lien, ouvert par Markdown.tsx */
const WEB_LINK = /^(?:https?:|mailto:|#)/i;

/** Cible d'un lien en clair : décodée, sans « file:/// » */
function decodedTarget(href: string): string {
  let value = href;
  try {
    value = decodeURIComponent(href);
  } catch {
    // « % » isolé : la cible telle quelle
  }
  return value.replace(/^file:\/\/\/?/i, '');
}

function samePath(a: string, b: string): boolean {
  const normal = (path: string) => path.replace(/\\/g, '/').replace(/\/+$/, '').toLowerCase();
  return normal(a) === normal(b);
}

/**
 * Lettres et chiffres des écritures à espaces (latin, grec, cyrillique) : un nom collé
 * à l'une d'elles est le bout d'un autre mot (« MyData.xlsx ») ; collé à du japonais,
 * du chinois, du coréen ou de l'arabe (« Data.xlsxの中身 »), il compte, comme côté
 * serveur (_WORD_CHARS de core/memory_documents.py)
 */
const WORD = '\\p{Script=Latin}\\p{Script=Greek}\\p{Script=Cyrillic}\\p{N}_';

/** Nom de la Mémoire présent, entier, dans un texte (casse ignorée) ; le plus long d'abord */
function memoryIn(texts: string[], memory: MemoryLink[]): MemoryLink | null {
  const candidates = [...memory].sort((a, b) => b.name.length - a.name.length);
  for (const link of candidates) {
    for (const name of new Set([link.name, link.text])) {
      const pattern = new RegExp(`(?<![${WORD}-])${escapeRegExp(name)}(?![${WORD}-])`, 'iu');
      if (texts.some((text) => pattern.test(text))) return link;
    }
  }
  return null;
}

/**
 * Lien Markdown vers autre chose qu'une page web : un chemin existant (cible),
 * ou un document ou un dossier de la Mémoire (cible ou texte du lien) ; null
 * sinon, le lien garde alors son seul texte (Markdown.tsx)
 */
function internalLink(node: HastNode, links: ChatLinks): HastNode | null {
  const href = node.properties?.href;
  if (typeof href !== 'string' || !href || WEB_LINK.test(href)) return null;
  const target = decodedTarget(href);
  const children = node.children ?? [];
  const path = links.paths.find(
    (item) => samePath(item.path, target) || samePath(item.text, target),
  );
  if (path)
    return { type: 'element', tagName: 'chat-path', properties: { path: path.path }, children };
  const memory = memoryIn([textOf(node), target], links.memory);
  return memory ? memoryElement(memory, children) : null;
}

function transform(
  node: HastNode,
  links: ChatLinks,
  pattern: RegExp,
  targets: Map<string, Target>,
  inCode: boolean,
): void {
  const children = node.children;
  if (!children) return;
  const next: HastNode[] = [];
  for (const child of children) {
    if (child.type === 'text') {
      const parts = splitText(child.value ?? '', links, pattern, targets, inCode);
      if (parts) next.push(...parts);
      else next.push(child);
      continue;
    }
    if (child.type === 'element') {
      const tag = child.tagName;
      // Lien existant : vers un chemin ou la Mémoire, sinon laissé tel quel
      if (tag === 'a') {
        next.push(internalLink(child, links) ?? child);
        continue;
      }
      // Bloc de code (pre) : laissé tel quel
      if (tag !== 'pre') transform(child, links, pattern, targets, inCode || tag === 'code');
    } else {
      transform(child, links, pattern, targets, inCode);
    }
    next.push(child);
  }
  node.children = next;
}

/** Greffon rehype : citations, chemins et noms de la Mémoire cliquables */
export function rehypeChatLinks(links: ChatLinks) {
  const targets = new Map<string, Target>();
  for (const item of links.memory) targets.set(item.text, { memory: item });
  // Un chemin passe avant un nom de la Mémoire écrit pareil
  for (const item of links.paths) targets.set(item.text, { path: item.path });
  // Du plus long au plus court : « C:\a\b.txt » avant « C:\a », « projet/a.md » avant « a.md ».
  // Un nom de la Mémoire, entier : ni « MyData.xlsx » pour « Data.xlsx », ni dans un
  // chemin ; collé au japonais, au chinois ou au coréen, il compte (WORD)
  const alternatives = [...targets.entries()]
    .sort(([a], [b]) => b.length - a.length)
    .map(([text, target]) =>
      'path' in target
        ? escapeRegExp(text)
        : `(?<![${WORD}./\\\\-])${escapeRegExp(text)}(?![${WORD}-]|\\.[${WORD}])`,
    );
  const source = alternatives.length
    ? `\\[(\\d{1,3})\\]|${alternatives.join('|')}`
    : '\\[(\\d{1,3})\\]';
  return () => (tree: HastNode) => {
    transform(tree, links, new RegExp(source, 'gu'), targets, false);
  };
}
