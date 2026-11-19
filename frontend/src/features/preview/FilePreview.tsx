/*
 * Aperçu d'un fichier, partagé par le volet de droite du chat, la fenêtre des
 * pièces jointes et le volet de la Mémoire (fileKinds.ts) :
 *  - image : en grand dans la place, un clic l'agrandit à la fenêtre (Lightbox) ;
 *  - audio, vidéo : le lecteur de la page ;
 *  - PDF, Word, Excel, PowerPoint, CSV : la page d'aperçu du serveur (lecteur
 *    PDF, visionneuse de Windows ou page HTML isolée) ;
 *  - Markdown rendu comme une réponse, HTML dans une iframe isolée comme un
 *    artefact, SVG en image ; leur source dans l'onglet Code ;
 *  - code coloré, texte tel quel ; un autre format lu comme du texte s'il en
 *    est, « pas d'aperçu » sinon.
 *
 * Le fichier n'est lu que par le serveur, qui ne sert que ce qu'il connaît
 * (pièce jointe, document produit ou cité, copie de la Mémoire).
 */

import {
  Code2,
  Eye,
  FileQuestion,
  FolderOpen,
  LoaderCircle,
  Music,
  SquareArrowOutUpRight,
} from 'lucide-react';
import { useMemo, useState } from 'react';

import { Button } from '../../components/ui/Button';
import { Lightbox } from '../../components/ui/Lightbox';
import { useT } from '../../i18n';
import { openFile, revealPath } from '../../lib/actions';
import { baseName, fileArtifact, formatLabel } from '../../lib/artifacts';
import { cn } from '../../lib/cn';
import {
  codeLanguage,
  type FileKind,
  fileKind,
  hasSource,
  isServerPreview,
} from '../../lib/fileKinds';
import { useFileInfo, useFileLink, useFileText } from '../../lib/files';
import { formatSize, formatWhen } from '../../lib/format';
import type { PreviewTab } from '../../stores/preview';
import { CodeBlock } from '../chat/markdown/CodeBlock';
import { Markdown } from '../chat/markdown/Markdown';
import { NativeDocument } from './NativeDocument';
import { usePreviewPage } from './usePreviewPage';

/** Iframe d'une page HTML : scripts, formulaires, fenêtres (navigateur du système) */
const HTML_SANDBOX = 'allow-scripts allow-forms allow-modals allow-popups';

/** Au-delà, le code s'affiche sans coloration (la page resterait figée le temps de colorer) */
const HIGHLIGHT_MAX = 150_000;

function Centered({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center text-sm text-fg-2">
      {children}
    </div>
  );
}

function Opening() {
  const t = useT();
  return (
    <div className="flex h-full items-center justify-center gap-2 text-sm text-fg-2">
      <LoaderCircle size={16} className="spin text-accent" />
      {t('preview.opening')}
    </div>
  );
}

/** Ce que l'on peut faire d'un fichier sans aperçu : l'ouvrir (produit par l'appli), le montrer */
function FileFallback({
  path,
  generated,
  message,
}: {
  path: string;
  generated: boolean;
  message: string;
}) {
  const t = useT();
  return (
    <Centered>
      <FileQuestion size={30} className="text-fg-3" aria-hidden />
      <span className="max-w-md">{message}</span>
      <div className="flex flex-wrap justify-center gap-2">
        {generated ? (
          <Button size="sm" onClick={() => void openFile(path)}>
            <SquareArrowOutUpRight size={14} /> {t('preview.openInApp')}
          </Button>
        ) : null}
        <Button size="sm" onClick={() => void revealPath(path)}>
          <FolderOpen size={14} /> {t('chat.file.reveal')}
        </Button>
      </div>
    </Centered>
  );
}

function ImagePreview({ path, generated }: { path: string; generated: boolean }) {
  const t = useT();
  const { url, settled } = useFileLink(path);
  const [zoom, setZoom] = useState(false);
  const name = baseName(path);
  if (!url) {
    return settled ? (
      <FileFallback path={path} generated={generated} message={t('preview.unavailable')} />
    ) : (
      <Opening />
    );
  }
  return (
    <div className="preview-checker flex h-full items-center justify-center overflow-auto p-6">
      <button
        type="button"
        onClick={() => setZoom(true)}
        aria-label={t('chat.image.enlarge', { name })}
        className="flex h-full w-full cursor-zoom-in items-center justify-center"
      >
        <img
          src={url}
          alt={name}
          draggable={false}
          className="max-h-full max-w-full rounded-sm object-contain shadow-md"
          style={{ animation: 'fade-in var(--motion) var(--motion-ease)' }}
        />
      </button>
      <Lightbox
        open={zoom}
        onOpenChange={setZoom}
        url={url}
        path={path}
        name={name}
        generated={generated}
      />
    </div>
  );
}

function MediaPreview({
  path,
  kind,
  generated,
}: {
  path: string;
  kind: FileKind;
  generated: boolean;
}) {
  const t = useT();
  const { url, settled } = useFileLink(path);
  if (!url) {
    return settled ? (
      <FileFallback path={path} generated={generated} message={t('preview.unavailable')} />
    ) : (
      <Opening />
    );
  }
  return (
    <div className="flex h-full flex-col items-center justify-center gap-4 p-6">
      {kind === 'video' ? (
        <video src={url} controls className="max-h-full max-w-full rounded-md bg-black" />
      ) : (
        <>
          <Music size={40} className="text-fg-3" aria-hidden />
          <audio src={url} controls className="w-full max-w-md" />
        </>
      )}
    </div>
  );
}

/** PDF, Office, CSV : page d'aperçu du serveur, ou visionneuse de Windows */
function ServerPreview({
  path,
  hidden,
  generated,
}: {
  path: string;
  hidden: boolean;
  generated: boolean;
}) {
  const artifact = useMemo(() => fileArtifact(path, generated), [path, generated]);
  const { view, error, fallback } = usePreviewPage(artifact);
  if (error) return <FileFallback path={path} generated={generated} message={error} />;
  if (!view) return <Opening />;
  if (view.kind === 'native') {
    return <NativeDocument key={view.id} view={view} hidden={hidden} onFailed={fallback} />;
  }
  return (
    <iframe
      key={view.id}
      src={view.url}
      title={view.title}
      // Sans allow-same-origin ; le PDF n'est pas isolé (le lecteur de WebView2
      // ne s'affiche pas en bac à sable), mais c'est le fichier lui-même, sans script
      sandbox={view.kind === 'pdf' ? undefined : ''}
      referrerPolicy="no-referrer"
      className={cn('h-full w-full border-0', hidden && 'pointer-events-none')}
    />
  );
}

/** Page HTML lue sur le disque : rendue comme un artefact (iframe isolée, ses scripts permis) */
function HtmlPreview({ code, title, hidden }: { code: string; title: string; hidden: boolean }) {
  const artifact = useMemo(
    () => ({ kind: 'html' as const, code, title, language: 'html', index: 0 }),
    [code, title],
  );
  const { view, error } = usePreviewPage(artifact);
  if (error) return <Centered>{error}</Centered>;
  if (!view) return <Opening />;
  return (
    <iframe
      key={view.id}
      src={view.url}
      title={view.title}
      sandbox={HTML_SANDBOX}
      referrerPolicy="no-referrer"
      className={cn('h-full w-full border-0 bg-white', hidden && 'pointer-events-none')}
    />
  );
}

export function CodeView({ code, lang }: { code: string; lang: string | undefined }) {
  return (
    <div className="md h-full overflow-auto p-3">
      <CodeBlock code={code} lang={code.length <= HIGHLIGHT_MAX ? lang : undefined} />
    </div>
  );
}

/** Texte tel quel : en chasse fixe (journal, texte brut), ou en prose (texte d'un document) */
export function PlainText({ text, prose = false }: { text: string; prose?: boolean }) {
  return (
    <pre
      dir="auto"
      className={cn(
        'h-full overflow-auto px-5 py-4 leading-relaxed break-words whitespace-pre-wrap text-fg',
        prose ? 'font-sans text-sm' : 'font-code text-[13px]',
      )}
    >
      {text}
    </pre>
  );
}

/**
 * Markdown rendu comme une réponse ; d'un fichier (file), son HTML aussi
 * (assaini) et les images de son dossier
 */
export function MarkdownView({ text, file = null }: { text: string; file?: string | null }) {
  return (
    <div className="h-full overflow-auto px-6 py-5">
      <Markdown text={text} file={file} className="mx-auto max-w-3xl" />
    </div>
  );
}

/** Bandeau au-dessus d'un aperçu (fichier tronqué, texte gardé en mémoire) */
export function PreviewNotice({ children }: { children: React.ReactNode }) {
  return (
    <p className="shrink-0 border-b border-line bg-bg-2 px-4 py-1.5 text-xs text-fg-2">
      {children}
    </p>
  );
}

function TextPreview({
  path,
  kind,
  tab,
  hidden,
  generated,
}: {
  path: string;
  kind: FileKind;
  tab: PreviewTab;
  hidden: boolean;
  generated: boolean;
}) {
  const t = useT();
  const { data, error, status } = useFileText(path);
  if (error) {
    // Format inconnu et binaire (415) : pas d'aperçu
    const message = status === 415 ? t('preview.none') : error;
    return <FileFallback path={path} generated={generated} message={message} />;
  }
  if (!data) return <Opening />;
  const source = tab === 'code' || !hasSource(kind);
  let body: React.ReactNode;
  if (kind === 'markdown' && !source) body = <MarkdownView text={data.text} file={path} />;
  else if (kind === 'html' && !source) {
    body = <HtmlPreview code={data.text} title={baseName(path)} hidden={hidden} />;
  } else if (kind === 'text' || kind === 'other') body = <PlainText text={data.text} />;
  else body = <CodeView code={data.text} lang={codeLanguage(path)} />;
  return (
    <div className="flex h-full flex-col">
      {data.truncated ? <PreviewNotice>{t('preview.truncated')}</PreviewNotice> : null}
      <div className="min-h-0 flex-1">{body}</div>
    </div>
  );
}

interface FilePreviewProps {
  path: string;
  /** Rendu, ou source (Markdown, HTML, SVG, CSV) */
  tab?: PreviewTab;
  /** Volet en mouvement (ouverture, fermeture) : visionneuse masquée, iframe sans pointeur */
  hidden?: boolean;
  /** Produit par l'appli : il s'ouvre aussi dans son application */
  generated?: boolean;
}

export function FilePreview({
  path,
  tab = 'preview',
  hidden = false,
  generated = false,
}: FilePreviewProps) {
  const kind = fileKind(path);
  if (kind === 'image' || (kind === 'svg' && tab === 'preview')) {
    return <ImagePreview path={path} generated={generated} />;
  }
  if (kind === 'audio' || kind === 'video') {
    return <MediaPreview path={path} kind={kind} generated={generated} />;
  }
  // CSV : son tableau (Excel, page du serveur), ou son texte (onglet Code)
  if (isServerPreview(kind) && !(kind === 'table' && tab === 'code')) {
    return <ServerPreview path={path} hidden={hidden} generated={generated} />;
  }
  return <TextPreview path={path} kind={kind} tab={tab} hidden={hidden} generated={generated} />;
}

// ── En-tête : icône, détails, onglets ──────────────────────────────────────

/**
 * « Markdown · 38,4 ko · il y a 7 heures » : format, taille et date du fichier
 * (lues au serveur), ou celles données (document de la Mémoire)
 */
export function FileMeta({
  path,
  size,
  date,
  className,
}: {
  path: string;
  size?: number | null | undefined;
  date?: string | null | undefined;
  className?: string;
}) {
  const known = size !== undefined || date !== undefined;
  const { data } = useFileInfo(known ? null : path);
  const parts = [
    formatLabel(path),
    formatSize(size ?? data?.size),
    formatWhen(date ?? data?.modified),
  ].filter(Boolean);
  return <span className={cn('truncate text-xs text-fg-3', className)}>{parts.join(' · ')}</span>;
}

/** Onglets Aperçu et Code d'un Markdown, d'une page HTML ou d'un SVG */
export function PreviewTabs({
  tab,
  onChange,
}: {
  tab: PreviewTab;
  onChange: (tab: PreviewTab) => void;
}) {
  const t = useT();
  return (
    <div
      role="tablist"
      aria-label={t('preview.display')}
      className="flex shrink-0 items-center rounded-md border border-line p-0.5"
    >
      {(
        [
          ['preview', t('common.preview'), Eye],
          ['code', t('preview.tab.code'), Code2],
        ] as const
      ).map(([id, label, Icon]) => (
        <button
          key={id}
          type="button"
          role="tab"
          aria-selected={tab === id}
          onClick={() => onChange(id)}
          className={cn(
            'flex h-6 items-center gap-1 rounded-sm px-2 text-xs font-medium transition-colors duration-150',
            tab === id ? 'bg-active text-fg' : 'text-fg-2 hover:text-fg',
          )}
        >
          <Icon size={13} />
          {label}
        </button>
      ))}
    </div>
  );
}
