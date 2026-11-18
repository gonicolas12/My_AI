/*
 * Volet d'aperçu de l'onglet Documents de la Mémoire, à droite du panneau
 * (clic sur un document, ou lien du chat vers lui) : comme l'aperçu d'un
 * fichier dans le chat (FilePreview), sur la copie de son fichier d'origine que
 * la Mémoire garde (memory_files.py). Un document rangé avant ces copies, ou
 * par le chat, n'en a pas : le volet montre le texte gardé en mémoire (la
 * description d'une image), en le disant.
 */

import { LoaderCircle, X } from 'lucide-react';
import { createElement, useEffect, useState } from 'react';

import { IconButton } from '../../../components/ui/Button';
import { useT } from '../../../i18n';
import { api, type MemoryDocument, type MemoryDocumentPreview } from '../../../lib/api';
import { codeLanguage, fileKind, hasSource } from '../../../lib/fileKinds';
import { useLoaded } from '../../../lib/files';
import { motionMs, PANE_MS, type PreviewTab } from '../../../stores/preview';
import {
  CodeView,
  FileMeta,
  FilePreview,
  MarkdownView,
  PlainText,
  PreviewNotice,
  PreviewTabs,
} from '../../preview/FilePreview';
import { fileIcon } from '../../preview/fileIcon';

/** Texte gardé en mémoire, faute de copie du fichier : rendu selon son format */
function StoredText({ preview, tab }: { preview: MemoryDocumentPreview; tab: PreviewTab }) {
  const t = useT();
  const kind = fileKind(preview.name);
  const image = kind === 'image' || preview.type === 'Image';
  const text = preview.text ?? '';
  let body: React.ReactNode;
  if (image) body = <MarkdownView text={text} />;
  // Markdown gardé en mémoire : son HTML rendu (assaini) ; ses images, sans dossier, en libellé
  else if (kind === 'markdown' && tab === 'preview') {
    body = <MarkdownView text={text} file={preview.name} />;
  } else if (kind === 'markdown' || kind === 'code') {
    body = <CodeView code={text} lang={codeLanguage(preview.name)} />;
  } else body = <PlainText text={text} prose />;
  return (
    <div className="flex h-full flex-col">
      <PreviewNotice>{image ? t('preview.storedImage') : t('preview.storedText')}</PreviewNotice>
      {preview.truncated ? <PreviewNotice>{t('preview.truncated')}</PreviewNotice> : null}
      <div className="min-h-0 flex-1">{body}</div>
    </div>
  );
}

interface MemoryPreviewProps {
  doc: MemoryDocument;
  /** Le volet se referme : la visionneuse Office se masque déjà */
  closing: boolean;
  onClose: () => void;
}

export function MemoryPreview({ doc, closing, onClose }: MemoryPreviewProps) {
  const t = useT();
  const { data: preview, error } = useLoaded(doc.id, (id) => api.memoryDocumentPreview(id));
  const [tab, setTab] = useState<PreviewTab>('preview');
  // Volet en train de s'ouvrir : la visionneuse Office attend sa place définitive
  const [moving, setMoving] = useState(true);
  useEffect(() => {
    const timer = setTimeout(() => setMoving(false), motionMs(PANE_MS));
    return () => clearTimeout(timer);
  }, []);

  const label = doc.folder ? doc.label : doc.name;
  // Copie du fichier : ses onglets selon son format ; texte en mémoire : un Markdown seul
  const kind = fileKind(preview?.path ?? doc.name);
  const tabs = preview ? (preview.path ? hasSource(kind) : kind === 'markdown') : false;

  let body: React.ReactNode;
  if (error) {
    body = (
      <div className="flex h-full items-center justify-center px-6 text-center text-sm text-fg-2">
        {error}
      </div>
    );
  } else if (!preview) {
    body = (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-fg-2">
        <LoaderCircle size={16} className="spin text-accent" />
        {t('preview.opening')}
      </div>
    );
  } else if (preview.path) {
    body = (
      <FilePreview key={preview.path} path={preview.path} tab={tab} hidden={moving || closing} />
    );
  } else {
    body = <StoredText preview={preview} tab={tab} />;
  }

  return (
    <section aria-label={t('common.preview')} className="flex h-full min-h-0 flex-col">
      {/* Aussi haut que l'en-tête du panneau : leurs bordures s'alignent (--aside-header) */}
      <header
        className="flex shrink-0 items-center gap-2 border-b border-line py-3 ps-4 pe-3"
        style={{ minHeight: 'var(--aside-header, 3.5rem)' }}
      >
        {createElement(fileIcon(doc.name), {
          size: 16,
          className: 'shrink-0 text-warning',
          'aria-hidden': true,
        })}
        <div className="flex min-w-0 flex-1 flex-col">
          <span className="truncate text-sm font-semibold" title={doc.name}>
            {label}
          </span>
          <FileMeta path={doc.name} size={preview?.size ?? null} date={doc.created} />
        </div>
        {tabs ? <PreviewTabs tab={tab} onChange={setTab} /> : null}
        <IconButton tooltipSide="left" label={t('preview.close')} onClick={onClose}>
          <X size={17} />
        </IconButton>
      </header>
      <div className="relative min-h-0 flex-1 bg-bg">{body}</div>
    </section>
  );
}
