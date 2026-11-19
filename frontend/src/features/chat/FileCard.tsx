/*
 * Fichiers d'une réponse : fichier généré (« génère un fichier… »), document
 * produit par un outil (Word, PDF…), image générée.
 *
 * Un clic sur le nom (ou sur l'image) l'affiche dans le volet d'aperçu de
 * droite, quel que soit son format. Comme dans l'interface Tk, il s'ouvre
 * aussi dans son application (ce sont des fichiers produits par l'appli), se
 * copie dans Téléchargements, ou se montre dans l'Explorateur.
 */

import {
  Download,
  FileCode2,
  FileText,
  FolderOpen,
  LoaderCircle,
  SquareArrowOutUpRight,
} from 'lucide-react';

import { IconButton } from '../../components/ui/Button';
import { useT } from '../../i18n';
import { openFile, revealPath, saveToDownloads } from '../../lib/actions';
import { baseName, formatLabel } from '../../lib/artifacts';
import { useFileUrl } from '../../lib/files';
import { revealLabels } from '../../lib/platform';

interface FileCardProps {
  /** Chemin du fichier ; vide tant qu'il n'est pas encore écrit */
  path: string;
  name?: string | undefined;
  kind: 'file' | 'document';
  /** Affiche le fichier dans le volet d'aperçu */
  onPreview: () => void;
}

export function FileCard({ path, name, kind, onPreview }: FileCardProps) {
  const t = useT();
  const shown = name || baseName(path);
  const Icon = kind === 'file' ? FileCode2 : FileText;
  const ready = Boolean(path);
  return (
    <div className="my-2 flex w-full max-w-md items-center gap-3 rounded-lg border border-line bg-bg-2 py-2 ps-2.5 pe-1.5">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent">
        {ready ? <Icon size={18} /> : <LoaderCircle size={17} className="spin" />}
      </span>
      <button
        type="button"
        disabled={!ready}
        onClick={onPreview}
        aria-label={t('chat.file.preview', { name: shown })}
        title={ready ? t('chat.file.preview', { name: shown }) : undefined}
        className="group min-w-0 flex-1 text-start"
      >
        <span className="block truncate text-sm font-medium text-link underline decoration-link/45 underline-offset-2 group-disabled:text-fg group-disabled:no-underline group-enabled:group-hover:decoration-link">
          {shown}
        </span>
        <span className="block truncate text-xs text-fg-3">{formatLabel(shown)}</span>
      </button>
      {ready ? (
        <div className="flex shrink-0 items-center">
          <IconButton label={t('preview.openInApp')} size="sm" onClick={() => void openFile(path)}>
            <SquareArrowOutUpRight size={15} />
          </IconButton>
          <IconButton
            label={t('chat.file.download')}
            size="sm"
            onClick={() => void saveToDownloads(path)}
          >
            <Download size={15} />
          </IconButton>
          <IconButton
            label={t(revealLabels().file)}
            size="sm"
            onClick={() => void revealPath(path)}
          >
            <FolderOpen size={15} />
          </IconButton>
        </div>
      ) : null}
    </div>
  );
}

/** Image générée : aperçu (420 px de large au plus, comme Tk), clic pour l'ouvrir dans le volet */
export function GeneratedImage({ path, onPreview }: { path: string; onPreview: () => void }) {
  const t = useT();
  const url = useFileUrl(path);
  const name = baseName(path);
  return (
    <figure className="my-2">
      <button
        type="button"
        onClick={onPreview}
        aria-label={t('chat.file.preview', { name })}
        className="block w-fit overflow-hidden rounded-lg border border-line bg-bg-2 transition-opacity duration-150 hover:opacity-90"
      >
        {url ? (
          <img
            src={url}
            alt={name}
            className="block max-h-[420px] max-w-[min(420px,100%)] object-contain"
            draggable={false}
          />
        ) : (
          <span className="block h-48 w-72 animate-pulse bg-bg-3" />
        )}
      </button>
      <figcaption className="mt-1 text-xs text-fg-3">
        <button
          type="button"
          onClick={onPreview}
          className="font-medium text-link underline decoration-link/45 underline-offset-2 hover:decoration-link"
        >
          {name}
        </button>
      </figcaption>
    </figure>
  );
}
