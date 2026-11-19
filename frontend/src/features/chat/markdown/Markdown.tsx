/*
 * Rendu Markdown des réponses de l'IA, et des fichiers Markdown en aperçu.
 *
 * - Contenu non fiable : aucun HTML brut dans une réponse (react-markdown
 *   l'affiche comme du texte), URL filtrées, liens ouverts dans le navigateur
 *   du système.
 * - Un fichier Markdown (aperçu, prop file) garde son HTML (<div align>,
 *   <img>, <br>, <details> d'un README) : lu par rehype-raw puis assaini comme
 *   sur GitHub (rehype-sanitize : ni script, ni gestionnaire d'événement, ni
 *   style). Ses images relatives se cherchent dans son dossier ; les images
 *   distantes restent des liens (appli hors ligne). Il est rendu d'un seul
 *   tenant, sans saut de ligne forcé, comme sur GitHub.
 * - Streaming : la réponse est découpée en blocs ; seuls les derniers sont
 *   relus et re-rendus, les blocs terminés gardent leur rendu (memo). Le
 *   Markdown incomplet du dernier bloc est refermé par remend.
 * - Un saut de ligne simple reste un saut de ligne, comme dans l'interface Tk
 *   et la PWA mobile (bloc « Sources », listes écrites sans ligne vide…).
 * - Citations « [n] », chemins de fichiers existants (aperçu dans le volet de
 *   droite), fichiers de la conversation nommés et documents ou dossiers de la
 *   Mémoire cliquables (links.ts), y compris dans un lien Markdown que le
 *   modèle invente (« [Dossier X](memory://x) »).
 */

import { FolderOpen, ImageIcon } from 'lucide-react';
import { createContext, memo, useContext, useMemo, useState } from 'react';
import ReactMarkdown, { type Components, type Options } from 'react-markdown';
import rehypeRaw from 'rehype-raw';
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
import remarkBreaks from 'remark-breaks';
import remarkGfm from 'remark-gfm';
import remend from 'remend';

import { ContextMenu, MenuItem } from '../../../components/ui/Menu';
import { useContextMenu } from '../../../components/ui/useContextMenu';
import { useT } from '../../../i18n';
import { revealPath } from '../../../lib/actions';
import { baseName } from '../../../lib/artifacts';
import { relativeImagePath, useMarkdownImage } from '../../../lib/files';
import { revealLabels } from '../../../lib/platform';
import { externalUrl } from '../../../lib/shell';
import { showInMemory } from '../../../stores/memory';
import { BlockSplitter } from './blocks';
import { CodeBlock } from './CodeBlock';
import { CodePreview } from './codePreview';
import { FileOpener } from './fileOpener';
import { type ChatLinks, prepareLinks, rehypeChatLinks } from './links';
import { prepareMath } from './math';
import { useMathPlugins } from './mathPlugins';

/** Vrai dans le dernier bloc d'une réponse en cours d'écriture */
const StreamingBlock = createContext(false);

/** Fichier Markdown en aperçu : ses images relatives se cherchent dans son dossier */
const MarkdownFile = createContext<string | null>(null);

/** Image d'un fichier Markdown, rangée dans son dossier : par un lien signé du serveur */
function FolderImage({
  file,
  path,
  alt,
  width,
  height,
}: {
  file: string;
  path: string;
  alt: string;
  width?: number | string | undefined;
  height?: number | string | undefined;
}) {
  const url = useMarkdownImage(file, path);
  if (!url) {
    return (
      <span className="md-image">
        <ImageIcon size={14} aria-hidden />
        {alt}
      </span>
    );
  }
  return <img src={url} alt={alt} width={width} height={height} className="md-file-image" />;
}

interface ImageProps {
  src?: string | Blob | undefined;
  alt?: string | undefined;
  width?: number | string | undefined;
  height?: number | string | undefined;
}

function MarkdownImage({ src, alt, width, height }: ImageProps) {
  const file = useContext(MarkdownFile);
  const label = alt || 'image';
  const source = typeof src === 'string' ? src : '';
  const local = file && source ? relativeImagePath(file, source) : null;
  if (file && local) {
    return <FolderImage file={file} path={local} alt={label} width={width} height={height} />;
  }
  // Les images distantes ne sont pas chargées (appli hors ligne) : un lien à la place
  const url = source ? externalUrl(source) : null;
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
}

/**
 * HTML d'un fichier Markdown : assaini comme sur GitHub ; les formules gardent
 * les classes que KaTeX lit ensuite
 */
const FILE_SCHEMA = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    code: [['className', /^language-./, 'math-inline', 'math-display']],
  },
};

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
  // Bloc HTML ou SVG d'une réponse finie : son bouton « Aperçu »
  const find = useContext(CodePreview);
  const onPreview = find && !streaming ? find(text) : null;
  return (
    <CodeBlock code={text} lang={languageOf(code)} streaming={streaming} onPreview={onPreview} />
  );
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
  img: MarkdownImage,
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

/**
 * Chemin existant, ou fichier de la conversation nommé : un fichier s'ouvre dans
 * l'aperçu (clic droit : Afficher dans l'Explorateur), un dossier dans
 * l'Explorateur ; jamais exécuté
 */
function FilePath({ node, children }: { node?: unknown; children?: React.ReactNode }) {
  const t = useT();
  const path = propertyOf(node, 'path');
  const folder = propertyOf(node, 'dir') === 'true';
  const openFile = useContext(FileOpener);
  const menu = useContextMenu();
  const open = () => (folder ? void revealPath(path) : openFile(path));
  // Élément en ligne, et non un bouton : un bouton forme une boîte insécable,
  // la ponctuation qui le suit passerait seule à la ligne
  return (
    <>
      <span
        role="link"
        tabIndex={0}
        className="md-path"
        title={folder ? t(revealLabels().path, { path }) : t('chat.path.preview', { path })}
        onClick={open}
        // Un dossier s'ouvre déjà dans l'Explorateur au clic : pas de menu
        onContextMenu={folder ? undefined : menu.open}
        onKeyDown={(event) => {
          if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            open();
          }
        }}
      >
        {children}
      </span>
      {folder ? null : (
        <ContextMenu at={menu.at} onClose={menu.close} origin={menu.origin} label={baseName(path)}>
          <MenuItem icon={<FolderOpen size={15} />} onSelect={() => void revealPath(path)}>
            {t(revealLabels().file)}
          </MenuItem>
        </ContextMenu>
      )}
    </>
  );
}

/**
 * Document ou dossier de la Mémoire cité : ouvre l'onglet Documents sur lui. Un
 * fichier d'un dossier : tout son dossier, ce fichier en évidence (cherché sur son
 * seul nom, le dossier n'aurait montré que lui)
 */
function MemoryRef({ node, children }: { node?: unknown; children?: React.ReactNode }) {
  const t = useT();
  const name = propertyOf(node, 'name');
  const folder = propertyOf(node, 'folder');
  const isDocument = propertyOf(node, 'kind') === 'document';
  const open = () => (isDocument ? showInMemory(folder || name, name) : showInMemory(name));
  // En ligne, comme un chemin : la ponctuation qui suit ne passe pas seule à la ligne
  return (
    <span
      role="link"
      tabIndex={0}
      className="md-memory"
      title={t('chat.memory.open', { name })}
      onClick={open}
      onKeyDown={(event) => {
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          open();
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
  'chat-memory': MemoryRef,
} as unknown as Components;

const ALL_COMPONENTS: Components = { ...COMPONENTS, ...LINK_COMPONENTS };

const REMARK_BASE: NonNullable<Options['remarkPlugins']> = [
  [remarkGfm, { singleTilde: false }],
  remarkBreaks,
];

/** Fichier Markdown : un saut de ligne simple n'en est pas un, comme sur GitHub */
const REMARK_FILE: NonNullable<Options['remarkPlugins']> = [[remarkGfm, { singleTilde: false }]];

/** HTML d'un fichier Markdown : lu, puis assaini (avant KaTeX, qui écrit le sien) */
const REHYPE_FILE: NonNullable<Options['rehypePlugins']> = [
  rehypeRaw,
  [rehypeSanitize, FILE_SCHEMA],
];

const Block = memo(function Block({
  text,
  links,
  file = false,
}: {
  text: string;
  links: ChatLinks | null;
  /** Fichier Markdown : son HTML est rendu (assaini) */
  file?: boolean;
}) {
  const linked = useMemo(() => prepareLinks(text), [text]);
  const prepared = useMemo(() => prepareMath(linked), [linked]);
  const math = useMathPlugins(prepared.hasMath);
  const base = file ? REMARK_FILE : REMARK_BASE;
  const remarkPlugins = math ? [...base, ...math.remark] : base;
  const rehypePlugins = useMemo(
    () => [
      ...(file ? REHYPE_FILE : []),
      ...(math?.rehype ?? []),
      ...(links ? [rehypeChatLinks(links)] : []),
    ],
    [file, math, links],
  );
  return (
    <ReactMarkdown
      remarkPlugins={remarkPlugins}
      rehypePlugins={rehypePlugins}
      components={ALL_COMPONENTS}
    >
      {math ? prepared.text : linked}
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
  /**
   * Chemin d'un fichier Markdown en aperçu : son HTML est rendu, assaini, et
   * ses images relatives cherchées dans son dossier ; rendu d'un seul tenant
   * (une balise ouverte dans un bloc se ferme dans un autre)
   */
  file?: string | null;
}

export const Markdown = memo(function Markdown({
  text,
  streaming,
  className,
  links = null,
  file = null,
}: MarkdownProps) {
  // Découpe incrémental propre à ce message : le texte en cours ne fait que s'allonger
  const [splitter] = useState(() => new BlockSplitter());
  const blocks = useMemo(() => (file ? [] : splitter.split(text)), [splitter, text, file]);
  const last = blocks.length - 1;
  if (file) {
    return (
      <div className={className ? `md ${className}` : 'md'}>
        <MarkdownFile.Provider value={file}>
          <Block text={text} links={links} file />
        </MarkdownFile.Provider>
      </div>
    );
  }
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
