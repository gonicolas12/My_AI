/*
 * Rendu Markdown des réponses de l'IA.
 *
 * - Contenu non fiable : aucun HTML brut (react-markdown l'affiche comme du
 *   texte), URL filtrées, liens ouverts dans le navigateur du système.
 * - Streaming : la réponse est découpée en blocs ; seuls les derniers sont
 *   relus et re-rendus, les blocs terminés gardent leur rendu (memo). Le
 *   Markdown incomplet du dernier bloc est refermé par remend.
 * - Un saut de ligne simple reste un saut de ligne, comme dans l'interface Tk
 *   et la PWA mobile (bloc « Sources », listes écrites sans ligne vide…).
 * - Citations « [n] » et chemins de fichiers existants cliquables (links.ts).
 */

import { ImageIcon } from 'lucide-react';
import { createContext, memo, useContext, useMemo, useState } from 'react';
import ReactMarkdown, { type Components, type Options } from 'react-markdown';
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';
import remend from 'remend';

import { revealPath } from '../../../lib/actions';
import { externalUrl } from '../../../lib/shell';
import { BlockSplitter } from './blocks';
import { CodeBlock } from './CodeBlock';
import { type ChatLinks, rehypeChatLinks } from './links';
import { prepareMath } from './math';
import { useMathPlugins } from './mathPlugins';

/** Vrai dans le dernier bloc d'une réponse en cours d'écriture */
const StreamingBlock = createContext(false);

interface HastText {
  type: 'text';
  value: string;
}

interface HastElement {
  type: 'element';
  tagName: string;
  properties?: { className?: unknown };
  children?: (HastElement | HastText)[];
}

function textOf(node: HastElement | HastText | undefined): string {
  if (!node) return '';
  if (node.type === 'text') return node.value;
  return (node.children ?? []).map(textOf).join('');
}

function languageOf(code: HastElement | undefined): string | undefined {
  const classes = code?.properties?.className;
  const list = Array.isArray(classes) ? (classes as unknown[]) : [];
  for (const item of list) {
    if (typeof item === 'string' && item.startsWith('language-')) {
      return item.slice('language-'.length);
    }
  }
  return undefined;
}

function Pre({ node }: { node?: unknown }) {
  const streaming = useContext(StreamingBlock);
  const element = node as HastElement | undefined;
  const code = element?.children?.find(
    (child): child is HastElement => child.type === 'element' && child.tagName === 'code',
  );
  // Le dernier saut de ligne d'un bloc de code n'est pas du contenu
  const text = textOf(code).replace(/\n$/, '');
  return <CodeBlock code={text} lang={languageOf(code)} streaming={streaming} />;
}

const COMPONENTS: Components = {
  pre: Pre,
  a({ href, children }) {
    const url = href ? externalUrl(href) : null;
    if (!url) return <span className="md-link-inert">{children}</span>;
    return (
      <a href={url} target="_blank" rel="noreferrer noopener" title={url}>
        {children}
      </a>
    );
  },
  img({ src, alt }) {
    // Les images distantes ne sont pas chargées (appli hors ligne) : un lien à la place
    const url = typeof src === 'string' ? externalUrl(src) : null;
    const label = alt || 'image';
    return url ? (
      <a href={url} target="_blank" rel="noreferrer noopener" className="md-image" title={url}>
        <ImageIcon size={14} aria-hidden />
        {label}
      </a>
    ) : (
      <span className="md-image">
        <ImageIcon size={14} aria-hidden />
        {label}
      </span>
    );
  },
  table({ children }) {
    return (
      <div className="md-table-wrap">
        <table>{children}</table>
      </div>
    );
  },
};

/** Élément ajouté par links.ts : ses propriétés hast */
function propertyOf(node: unknown, name: string): string {
  const properties = (node as { properties?: Record<string, unknown> } | undefined)?.properties;
  const value = properties?.[name];
  return typeof value === 'string' ? value : '';
}

/** Citation « [n] » : lien vers sa source, ouvert dans le navigateur du système */
function Citation({ node, children }: { node?: unknown; children?: React.ReactNode }) {
  const url = externalUrl(propertyOf(node, 'href'));
  if (!url) return <>{children}</>;
  return (
    <a href={url} className="md-cite" title={url} target="_blank" rel="noreferrer noopener">
      {children}
    </a>
  );
}

/** Chemin existant : montré dans l'Explorateur, jamais ouvert ni exécuté */
function FilePath({ node, children }: { node?: unknown; children?: React.ReactNode }) {
  const path = propertyOf(node, 'path');
  // Élément en ligne, et non un bouton : un bouton forme une boîte insécable,
  // la ponctuation qui le suit passerait seule à la ligne
  return (
    <span
      role="link"
      tabIndex={0}
      className="md-path"
      title={`Afficher dans l’Explorateur : ${path}`}
      onClick={() => void revealPath(path)}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          void revealPath(path);
        }
      }}
    >
      {children}
    </span>
  );
}

// Éléments propres à l'appli, hors du vocabulaire HTML de react-markdown
const LINK_COMPONENTS = {
  'chat-cite': Citation,
  'chat-path': FilePath,
} as unknown as Components;

const ALL_COMPONENTS: Components = { ...COMPONENTS, ...LINK_COMPONENTS };

const REMARK_BASE: NonNullable<Options['remarkPlugins']> = [
  [remarkGfm, { singleTilde: false }],
  remarkBreaks,
];

const Block = memo(function Block({ text, links }: { text: string; links: ChatLinks | null }) {
  const prepared = useMemo(() => prepareMath(text), [text]);
  const math = useMathPlugins(prepared.hasMath);
  const remarkPlugins = math ? [...REMARK_BASE, ...math.remark] : REMARK_BASE;
  const rehypePlugins = useMemo(
    () => [...(math?.rehype ?? []), ...(links ? [rehypeChatLinks(links)] : [])],
    [math, links],
  );
  return (
    <ReactMarkdown
      remarkPlugins={remarkPlugins}
      rehypePlugins={rehypePlugins}
      components={ALL_COMPONENTS}
    >
      {math ? prepared.text : text}
    </ReactMarkdown>
  );
});

interface MarkdownProps {
  text: string;
  /** Réponse en cours d'écriture */
  streaming?: boolean;
  className?: string;
  /** Citations et chemins à rendre cliquables (référence stable) */
  links?: ChatLinks | null;
}

export const Markdown = memo(function Markdown({
  text,
  streaming,
  className,
  links = null,
}: MarkdownProps) {
  // Découpe incrémental propre à ce message : le texte en cours ne fait que s'allonger
  const [splitter] = useState(() => new BlockSplitter());
  const blocks = useMemo(() => splitter.split(text), [splitter, text]);
  const last = blocks.length - 1;
  return (
    <div className={className ? `md ${className}` : 'md'}>
      {blocks.map((block, index) => {
        const open = Boolean(streaming) && index === last;
        return (
          <StreamingBlock.Provider value={open} key={index}>
            <Block text={open ? remend(block) : block} links={links} />
          </StreamingBlock.Provider>
        );
      })}
    </div>
  );
});
