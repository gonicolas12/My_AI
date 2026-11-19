/*
 * Volet d'aperçu, qui s'élargit depuis la droite : rendu en direct d'un bloc
 * HTML/SVG d'une réponse (onglets Aperçu et Code), ou d'un fichier cliqué dans
 * le chat ou la page Code (FilePreview : image, code, Markdown, PDF, Word,
 * Excel…). Il se referme de même, jamais d'un coup. Chacune des deux pages a
 * le sien (PreviewPane page=…).
 *
 * La page d'aperçu s'affiche dans une iframe isolée, sans allow-same-origin :
 * elle ne peut ni lire l'appli ni appeler son API (cf. interfaces/desktop/previews.py).
 */

import {
  ChevronLeft,
  ChevronRight,
  Eye,
  FolderOpen,
  Globe,
  SquareArrowOutUpRight,
  X,
} from 'lucide-react';
import { createElement, useEffect, useRef, useState } from 'react';

import { IconButton } from '../../components/ui/Button';
import { isRtl, useLocale, useT } from '../../i18n';
import { openFile, revealPath } from '../../lib/actions';
import { api } from '../../lib/api';
import type { Artifact } from '../../lib/artifacts';
import { cn } from '../../lib/cn';
import { fileKind, hasSource } from '../../lib/fileKinds';
import { notify, type Tab } from '../../stores/app';
import {
  closePreview,
  motionMs,
  PANE_MS,
  PREVIEW_WIDTH,
  setPreviewTab,
  setPreviewWidth,
  showPreviewItem,
  usePreview,
} from '../../stores/preview';
import { ArtifactView } from './ArtifactView';
import { FileMeta, FilePreview, PreviewTabs } from './FilePreview';
import { fileIcon } from './fileIcon';
import { usePreviewPage } from './usePreviewPage';

/** Largeur gardée à la conversation quand le volet s'élargit (px) */
const CHAT_MIN_WIDTH = 420;

function maxWidth(): number {
  return Math.max(PREVIEW_WIDTH.min, window.innerWidth - CHAT_MIN_WIDTH);
}

/**
 * Poignée du bord côté conversation (à gauche, à droite en arabe) : glisser
 * vers la conversation élargit le volet
 */
function ResizeHandle({ onDrag }: { onDrag: (dragging: boolean) => void }) {
  const t = useT();
  const rtl = isRtl(useLocale());
  const width = usePreview((state) => state.width);
  const start = useRef<{ x: number; width: number } | null>(null);

  const move = (event: React.PointerEvent) => {
    if (!start.current) return;
    const moved = start.current.x - event.clientX;
    const next = start.current.width + (rtl ? -moved : moved);
    setPreviewWidth(Math.min(next, maxWidth()));
  };
  const end = (event: React.PointerEvent) => {
    if (!start.current) return;
    start.current = null;
    event.currentTarget.releasePointerCapture(event.pointerId);
    onDrag(false);
    setPreviewWidth(usePreview.getState().width, true);
  };

  return (
    <div
      role="separator"
      aria-orientation="vertical"
      aria-label={t('preview.resize')}
      aria-valuemin={PREVIEW_WIDTH.min}
      aria-valuemax={PREVIEW_WIDTH.max}
      aria-valuenow={width}
      tabIndex={0}
      onPointerDown={(event) => {
        start.current = { x: event.clientX, width };
        event.currentTarget.setPointerCapture(event.pointerId);
        onDrag(true);
      }}
      onPointerMove={move}
      onPointerUp={end}
      onPointerCancel={end}
      onKeyDown={(event) => {
        const step = event.shiftKey ? 64 : 16;
        const widen = rtl ? 'ArrowRight' : 'ArrowLeft';
        const narrow = rtl ? 'ArrowLeft' : 'ArrowRight';
        if (event.key === widen) setPreviewWidth(Math.min(width + step, maxWidth()), true);
        else if (event.key === narrow) setPreviewWidth(width - step, true);
        else return;
        event.preventDefault();
      }}
      className="group absolute top-0 bottom-0 -start-[3px] z-10 w-[6px] cursor-col-resize outline-none"
    >
      <span className="mx-auto block h-full w-px bg-line transition-colors duration-150 group-hover:w-[2px] group-hover:bg-accent group-focus-visible:w-[2px] group-focus-visible:bg-accent" />
    </div>
  );
}

function PreviewBody({ artifact, hidden }: { artifact: Artifact; hidden: boolean }) {
  const tab = usePreview((state) => state.tab);
  if (artifact.kind === 'document') {
    return (
      <FilePreview
        key={artifact.path}
        path={artifact.path}
        tab={tab}
        hidden={hidden}
        generated={artifact.generated}
      />
    );
  }
  return <ArtifactView artifact={artifact} tab={tab} hidden={hidden} />;
}

/** Volet en mouvement (ouverture) : la visionneuse Office attend sa place définitive */
function useSettling(): boolean {
  const [moving, setMoving] = useState(true);
  useEffect(() => {
    const timer = setTimeout(() => setMoving(false), motionMs(PANE_MS));
    return () => clearTimeout(timer);
  }, []);
  return moving;
}

// Infobulles de l'en-tête à gauche : en dessous, elles passeraient sous une visionneuse Office
function OpenPane() {
  const t = useT();
  const items = usePreview((state) => state.items);
  const index = usePreview((state) => state.index);
  const tab = usePreview((state) => state.tab);
  const width = usePreview((state) => state.width);
  const closing = usePreview((state) => state.closing);
  const [dragging, setDragging] = useState(false);
  const moving = useSettling();
  const artifact = items[index];
  const { view } = usePreviewPage(artifact);

  // La fenêtre rétrécit : le volet laisse sa place à la conversation
  useEffect(() => {
    const onResize = () => {
      if (usePreview.getState().width > maxWidth()) setPreviewWidth(maxWidth());
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, []);

  if (!artifact) return null;
  const isDocument = artifact.kind === 'document';
  const kind = isDocument ? fileKind(artifact.path) : null;
  const shown = Math.min(width, maxWidth());
  // Ouverture, fermeture : la visionneuse Office attend. Redimensionnement : tout
  // suit la poignée, elle comprise (le corps ne prend pas le pointeur entre-temps)
  const hidden = moving || closing;

  const openInBrowser = () => {
    if (!view) return;
    api.previewInBrowser(view.id).catch((error: unknown) => {
      notify('error', error instanceof Error ? error.message : String(error));
    });
  };

  return (
    <aside
      aria-label={t('common.preview')}
      className={cn(
        'relative h-full shrink-0 border-s border-line bg-bg-2',
        closing ? 'pane-close' : 'pane-open',
        // En mouvement, le contenu à sa largeur finale est rogné ; ensuite, la
        // poignée déborde de 3 px sur la conversation
        (moving || closing) && 'overflow-hidden',
      )}
      style={{ width: shown }}
    >
      {/* Contenu à sa largeur finale : il ne se recompose pas pendant que le volet s'élargit */}
      <div className="relative flex h-full flex-col" style={{ width: shown }}>
        <ResizeHandle onDrag={setDragging} />
        <header className="flex h-12 shrink-0 items-center gap-1.5 border-b border-line ps-3 pe-2">
          {isDocument ? (
            createElement(fileIcon(artifact.path), {
              size: 16,
              className: 'shrink-0 text-accent',
              'aria-hidden': true,
            })
          ) : (
            <Eye size={16} className="shrink-0 text-accent" aria-hidden />
          )}
          {/* Nom en entier, détails dessous : le nom n'est pas coupé pour eux */}
          <div className="flex min-w-0 flex-1 flex-col">
            <span className="truncate text-sm leading-5 font-semibold" title={artifact.title}>
              {artifact.title}
            </span>
            {isDocument ? <FileMeta path={artifact.path} className="leading-4" /> : null}
          </div>
          {items.length > 1 ? (
            <div className="flex items-center text-xs text-fg-2 tabular-nums">
              <IconButton
                tooltipSide="left"
                label={t('preview.previous')}
                size="sm"
                disabled={index <= 0}
                onClick={() => showPreviewItem(index - 1)}
              >
                <ChevronLeft size={15} className="rtl:-scale-x-100" />
              </IconButton>
              <span className="px-0.5">
                {index + 1}/{items.length}
              </span>
              <IconButton
                tooltipSide="left"
                label={t('preview.next')}
                size="sm"
                disabled={index >= items.length - 1}
                onClick={() => showPreviewItem(index + 1)}
              >
                <ChevronRight size={15} className="rtl:-scale-x-100" />
              </IconButton>
            </div>
          ) : null}
          {!isDocument || (kind && hasSource(kind)) ? (
            <PreviewTabs tab={tab} onChange={setPreviewTab} />
          ) : null}
          {isDocument && artifact.generated ? (
            <IconButton
              tooltipSide="left"
              label={t('preview.openInApp')}
              onClick={() => void openFile(artifact.path)}
            >
              <SquareArrowOutUpRight size={16} />
            </IconButton>
          ) : null}
          {isDocument ? (
            <IconButton
              tooltipSide="left"
              label={t('chat.file.reveal')}
              onClick={() => void revealPath(artifact.path)}
            >
              <FolderOpen size={16} />
            </IconButton>
          ) : null}
          {view ? (
            <IconButton
              tooltipSide="left"
              label={t('preview.openInBrowser')}
              onClick={openInBrowser}
            >
              <Globe size={16} />
            </IconButton>
          ) : null}
          <IconButton tooltipSide="left" label={t('preview.close')} onClick={closePreview}>
            <X size={17} />
          </IconButton>
        </header>
        <div className={cn('relative min-h-0 flex-1 bg-bg', dragging && 'pointer-events-none')}>
          <PreviewBody artifact={artifact} hidden={hidden} />
        </div>
      </div>
    </aside>
  );
}

/** Volet de la page `page` : celui d'une autre page n'y paraît pas */
export function PreviewPane({ page }: { page: Tab }) {
  const shown = usePreview((state) => state.open && state.page === page && state.items.length > 0);
  if (!shown) return null;
  return <OpenPane />;
}
