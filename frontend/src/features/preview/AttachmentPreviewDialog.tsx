/*
 * Fenêtre d'aperçu au premier plan de l'appli, comme un panneau (Réglages,
 * Mémoire…), un peu plus grande : pièce jointe pas encore envoyée, et tout ce
 * que la page Agents montre (pièce jointe d'un fil, fichier cité par un agent,
 * bloc HTML ou SVG de son résultat). Elle monte en s'ouvrant et s'efface en se
 * fermant (dialog-rise, index.css) ; Échap ou un clic à côté la ferment.
 * Plusieurs éléments : elle passe de l'un à l'autre (‹ k/n ›).
 */

import * as RadixDialog from '@radix-ui/react-dialog';
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
import { useT } from '../../i18n';
import { openFile, revealPath } from '../../lib/actions';
import { api } from '../../lib/api';
import { fileKind, hasSource } from '../../lib/fileKinds';
import { notify } from '../../stores/app';
import {
  closeAttachmentPreview,
  setAttachmentPreviewTab,
  showAttachmentPreviewItem,
  useAttachmentPreview,
} from '../../stores/attachmentPreview';
import { motionMs, PANE_MS } from '../../stores/preview';
import { ArtifactView } from './ArtifactView';
import { FileMeta, FilePreview, PreviewTabs } from './FilePreview';
import { fileIcon } from './fileIcon';
import { usePreviewPage } from './usePreviewPage';

/** Taille de la fenêtre : un peu plus que les Réglages (860 × 760) */
const DIALOG_WIDTH = 1120;

/** Contenu, monté avec la fenêtre : la visionneuse Office attend qu'elle ait fini de monter */
function DialogBody() {
  const t = useT();
  const open = useAttachmentPreview((state) => state.open);
  const items = useAttachmentPreview((state) => state.items);
  const index = useAttachmentPreview((state) => state.index);
  const tab = useAttachmentPreview((state) => state.tab);
  const [moving, setMoving] = useState(true);
  useEffect(() => {
    const timer = setTimeout(() => setMoving(false), motionMs(PANE_MS));
    return () => clearTimeout(timer);
  }, []);

  const item = items[index];
  // Page d'aperçu d'un bloc HTML/SVG : elle s'ouvre aussi dans le navigateur
  const { view } = usePreviewPage(item?.kind !== 'document' ? item : undefined);
  if (!item) return null;
  const isDocument = item.kind === 'document';
  const kind = isDocument ? fileKind(item.path) : null;
  const hidden = moving || !open;

  const openInBrowser = () => {
    if (!view) return;
    api.previewInBrowser(view.id).catch((error: unknown) => {
      notify('error', error instanceof Error ? error.message : String(error));
    });
  };

  return (
    <>
      <header className="flex h-14 shrink-0 items-center gap-2 border-b border-line ps-4 pe-2">
        <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent">
          {isDocument ? (
            createElement(fileIcon(item.path), { size: 16, 'aria-hidden': true })
          ) : (
            <Eye size={16} aria-hidden />
          )}
        </span>
        <div className="flex min-w-0 flex-1 flex-col">
          <RadixDialog.Title
            className="truncate text-sm leading-5 font-semibold"
            title={isDocument ? item.path : item.title}
          >
            {item.title}
          </RadixDialog.Title>
          <RadixDialog.Description className="truncate text-xs leading-4 text-fg-2">
            {isDocument ? <FileMeta path={item.path} /> : item.kind.toUpperCase()}
          </RadixDialog.Description>
        </div>
        {items.length > 1 ? (
          <div className="flex items-center text-xs text-fg-2 tabular-nums">
            <IconButton
              label={t('preview.previous')}
              size="sm"
              disabled={index <= 0}
              onClick={() => showAttachmentPreviewItem(index - 1)}
            >
              <ChevronLeft size={15} className="rtl:-scale-x-100" />
            </IconButton>
            <span className="px-0.5">
              {index + 1}/{items.length}
            </span>
            <IconButton
              label={t('preview.next')}
              size="sm"
              disabled={index >= items.length - 1}
              onClick={() => showAttachmentPreviewItem(index + 1)}
            >
              <ChevronRight size={15} className="rtl:-scale-x-100" />
            </IconButton>
          </div>
        ) : null}
        {!isDocument || (kind && hasSource(kind)) ? (
          <PreviewTabs tab={tab} onChange={setAttachmentPreviewTab} />
        ) : null}
        {isDocument && item.generated ? (
          <IconButton
            tooltipSide="left"
            label={t('preview.openInApp')}
            onClick={() => void openFile(item.path)}
          >
            <SquareArrowOutUpRight size={16} />
          </IconButton>
        ) : null}
        {isDocument ? (
          <IconButton
            tooltipSide="left"
            label={t('chat.file.reveal')}
            onClick={() => void revealPath(item.path)}
          >
            <FolderOpen size={16} />
          </IconButton>
        ) : null}
        {!isDocument && view ? (
          <IconButton tooltipSide="left" label={t('preview.openInBrowser')} onClick={openInBrowser}>
            <Globe size={16} />
          </IconButton>
        ) : null}
        <RadixDialog.Close asChild>
          <IconButton tooltipSide="left" label={t('preview.close')} shortcut="Escape">
            <X size={18} />
          </IconButton>
        </RadixDialog.Close>
      </header>
      <div className="relative min-h-0 flex-1 bg-bg">
        {isDocument ? (
          <FilePreview
            key={item.path}
            path={item.path}
            tab={tab}
            hidden={hidden}
            generated={item.generated}
          />
        ) : (
          <ArtifactView key={`${index}:${item.title}`} artifact={item} tab={tab} hidden={hidden} />
        )}
      </div>
    </>
  );
}

export function AttachmentPreviewDialog() {
  const open = useAttachmentPreview((state) => state.open);
  const contentRef = useRef<HTMLDivElement>(null);
  return (
    <RadixDialog.Root
      open={open}
      onOpenChange={(next) => {
        if (!next) closeAttachmentPreview();
      }}
    >
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="dialog-scrim fixed inset-0 z-40 bg-scrim" />
        <RadixDialog.Content
          className="dialog-rise fixed top-1/2 left-1/2 z-50 flex h-[min(900px,calc(100vh-48px))] w-[calc(100vw-32px)] -translate-x-1/2 -translate-y-1/2 flex-col overflow-hidden rounded-lg border border-line bg-bg-2 text-fg shadow-lg focus:outline-none"
          style={{ maxWidth: DIALOG_WIDTH }}
          // Focus sur la fenêtre, pas sur sa croix : son infobulle ne s'ouvre pas d'elle-même
          onOpenAutoFocus={(event) => {
            event.preventDefault();
            contentRef.current?.focus();
          }}
          ref={contentRef}
        >
          <DialogBody />
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
