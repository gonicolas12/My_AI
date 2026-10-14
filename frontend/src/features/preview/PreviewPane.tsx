/*
 * Volet d'aperçu, qui glisse depuis la droite : rendu en direct d'un bloc
 * HTML/SVG d'une réponse (onglets Aperçu et Code), ou d'un document (PDF par
 * le lecteur de WebView2, autres formats en page HTML).
 *
 * La page d'aperçu s'affiche dans une iframe isolée, sans allow-same-origin :
 * elle ne peut ni lire l'appli ni appeler son API (cf. interfaces/desktop/previews.py).
 */

import {
  ChevronLeft,
  ChevronRight,
  Code2,
  Eye,
  FileText,
  FolderOpen,
  Globe,
  LoaderCircle,
  X,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { IconButton } from '../../components/ui/Button';
import { openFile, revealPath } from '../../lib/actions';
import { api } from '../../lib/api';
import type { Artifact } from '../../lib/artifacts';
import { cn } from '../../lib/cn';
import { notify } from '../../stores/app';
import {
  closePreview,
  PREVIEW_WIDTH,
  setPreviewTab,
  setPreviewWidth,
  showPreviewItem,
  usePreview,
} from '../../stores/preview';
import { CodeBlock } from '../chat/markdown/CodeBlock';
import { NativeDocument } from './NativeDocument';
import { usePreviewPage } from './usePreviewPage';

/** Largeur gardée à la conversation quand le volet s'élargit (px) */
const CHAT_MIN_WIDTH = 420;

/** Iframe d'un artefact : scripts, formulaires, fenêtres (navigateur du système) */
const ARTIFACT_SANDBOX = 'allow-scripts allow-forms allow-modals allow-popups';

function maxWidth(): number {
  return Math.max(PREVIEW_WIDTH.min, window.innerWidth - CHAT_MIN_WIDTH);
}

/** Poignée du bord gauche : glisser vers la gauche élargit le volet */
function ResizeHandle({ onDrag }: { onDrag: (dragging: boolean) => void }) {
  const width = usePreview((state) => state.width);
  const start = useRef<{ x: number; width: number } | null>(null);

  const move = (event: React.PointerEvent) => {
    if (!start.current) return;
    const next = start.current.width + (start.current.x - event.clientX);
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
      aria-label="Largeur du volet d'aperçu"
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
        if (event.key === 'ArrowLeft') setPreviewWidth(Math.min(width + step, maxWidth()), true);
        else if (event.key === 'ArrowRight') setPreviewWidth(width - step, true);
        else return;
        event.preventDefault();
      }}
      className="group absolute top-0 bottom-0 -left-[3px] z-10 w-[6px] cursor-col-resize outline-none"
    >
      <span className="mx-auto block h-full w-px bg-line transition-colors duration-150 group-hover:w-[2px] group-hover:bg-accent group-focus-visible:w-[2px] group-focus-visible:bg-accent" />
    </div>
  );
}

function PreviewBody({ artifact, dragging }: { artifact: Artifact; dragging: boolean }) {
  const tab = usePreview((state) => state.tab);
  const { view, error, fallback } = usePreviewPage(artifact);

  if (tab === 'code' && artifact.kind !== 'document') {
    return (
      <div className="md h-full overflow-auto p-3">
        <CodeBlock code={artifact.code} lang={artifact.language || artifact.kind} />
      </div>
    );
  }
  if (error) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-3 px-6 text-center text-sm text-fg-2">
        <span>{error}</span>
        {artifact.kind === 'document' ? (
          <button
            type="button"
            className="text-link underline-offset-2 hover:underline"
            onClick={() => void revealPath(artifact.path)}
          >
            Afficher dans l’Explorateur
          </button>
        ) : null}
      </div>
    );
  }
  if (!view) {
    return (
      <div className="flex h-full items-center justify-center gap-2 text-sm text-fg-2">
        <LoaderCircle size={16} className="spin text-accent" />
        Ouverture de l’aperçu…
      </div>
    );
  }
  if (view.kind === 'native') {
    return <NativeDocument key={view.id} view={view} hidden={dragging} onFailed={fallback} />;
  }
  return (
    <iframe
      key={view.id}
      src={view.url}
      title={view.title}
      // Pas d'allow-same-origin : la page ne peut ni lire l'appli ni appeler son API.
      // Le PDF n'est pas isolé : le lecteur de WebView2 ne s'affiche pas en bac à sable.
      sandbox={view.kind === 'pdf' ? undefined : view.kind === 'document' ? '' : ARTIFACT_SANDBOX}
      referrerPolicy="no-referrer"
      className={cn('h-full w-full border-0', dragging && 'pointer-events-none')}
    />
  );
}

// Infobulles de l'en-tête à gauche : en dessous, elles passeraient sous une visionneuse Office
export function PreviewPane() {
  const open = usePreview((state) => state.open);
  const items = usePreview((state) => state.items);
  const index = usePreview((state) => state.index);
  const tab = usePreview((state) => state.tab);
  const width = usePreview((state) => state.width);
  const [dragging, setDragging] = useState(false);
  const { view } = usePreviewPage(open ? items[index] : undefined);

  // La fenêtre rétrécit : le volet laisse sa place à la conversation
  useEffect(() => {
    if (!open) return undefined;
    const onResize = () => {
      if (usePreview.getState().width > maxWidth()) setPreviewWidth(maxWidth());
    };
    window.addEventListener('resize', onResize);
    return () => window.removeEventListener('resize', onResize);
  }, [open]);

  const artifact = items[index];
  if (!open || !artifact) return null;
  const isDocument = artifact.kind === 'document';

  const openInBrowser = () => {
    if (!view) return;
    api.previewInBrowser(view.id).catch((error: unknown) => {
      notify('error', error instanceof Error ? error.message : String(error));
    });
  };

  return (
    <aside
      aria-label="Aperçu"
      className="relative flex h-full shrink-0 flex-col border-l border-line bg-bg-2"
      style={{
        width: Math.min(width, maxWidth()),
        animation: 'slide-in-right var(--motion) var(--motion-ease)',
      }}
    >
      <ResizeHandle onDrag={setDragging} />
      <header className="flex h-12 shrink-0 items-center gap-1.5 border-b border-line pr-2 pl-3">
        {isDocument ? (
          <FileText size={16} className="shrink-0 text-accent" />
        ) : (
          <Eye size={16} className="shrink-0 text-accent" />
        )}
        <span className="min-w-0 flex-1 truncate text-sm font-semibold" title={artifact.title}>
          {artifact.title}
        </span>
        {items.length > 1 ? (
          <div className="flex items-center text-xs text-fg-2 tabular-nums">
            <IconButton
              tooltipSide="left"
              label="Aperçu précédent"
              size="sm"
              disabled={index <= 0}
              onClick={() => showPreviewItem(index - 1)}
            >
              <ChevronLeft size={15} />
            </IconButton>
            <span className="px-0.5">
              {index + 1}/{items.length}
            </span>
            <IconButton
              tooltipSide="left"
              label="Aperçu suivant"
              size="sm"
              disabled={index >= items.length - 1}
              onClick={() => showPreviewItem(index + 1)}
            >
              <ChevronRight size={15} />
            </IconButton>
          </div>
        ) : null}
        {!isDocument ? (
          <div
            role="tablist"
            aria-label="Affichage"
            className="flex items-center rounded-md border border-line p-0.5"
          >
            {(
              [
                ['preview', 'Aperçu', Eye],
                ['code', 'Code', Code2],
              ] as const
            ).map(([id, label, Icon]) => (
              <button
                key={id}
                type="button"
                role="tab"
                aria-selected={tab === id}
                onClick={() => setPreviewTab(id)}
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
        ) : null}
        {isDocument && artifact.generated ? (
          <IconButton
            tooltipSide="left"
            label="Ouvrir dans son application"
            onClick={() => void openFile(artifact.path)}
          >
            <FolderOpen size={16} />
          </IconButton>
        ) : null}
        {isDocument && !artifact.generated ? (
          <IconButton
            tooltipSide="left"
            label="Afficher dans l’Explorateur"
            onClick={() => void revealPath(artifact.path)}
          >
            <FolderOpen size={16} />
          </IconButton>
        ) : null}
        <IconButton
          tooltipSide="left"
          label="Ouvrir dans le navigateur"
          disabled={!view}
          onClick={openInBrowser}
        >
          <Globe size={16} />
        </IconButton>
        <IconButton tooltipSide="left" label="Fermer l’aperçu" onClick={closePreview}>
          <X size={17} />
        </IconButton>
      </header>
      <div className="relative min-h-0 flex-1 bg-bg">
        <PreviewBody artifact={artifact} dragging={dragging} />
      </div>
    </aside>
  );
}
