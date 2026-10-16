/*
 * Fichiers d'une réponse : fichier généré (« génère un fichier… »), document
 * produit par un outil (Word, PDF…), image générée.
 *
 * Comme dans l'interface Tk, le fichier s'ouvre dans son application (ce sont
 * des fichiers produits par l'appli), se copie dans Téléchargements (clic sur
 * le nom dans Tk), s'affiche dans le volet d'aperçu s'il en a un, ou se montre
 * dans l'Explorateur.
 */

import { Download, Eye, FileCode2, FileText, FolderOpen, LoaderCircle } from 'lucide-react';
import { useState } from 'react';

import { IconButton } from '../../components/ui/Button';
import { Lightbox } from '../../components/ui/Lightbox';
import { openFile, revealPath, saveToDownloads } from '../../lib/actions';
import { baseName, formatLabel } from '../../lib/artifacts';
import { useFileUrl } from '../../lib/files';

interface FileCardProps {
  /** Chemin du fichier ; vide tant qu'il n'est pas encore écrit */
  path: string;
  name?: string | undefined;
  kind: 'file' | 'document';
  /** Ouvre l'aperçu du document dans le volet (formats qui en ont un) */
  onPreview?: (() => void) | undefined;
}

export function FileCard({ path, name, kind, onPreview }: FileCardProps) {
  const shown = name || baseName(path);
  const Icon = kind === 'file' ? FileCode2 : FileText;
  const ready = Boolean(path);
  return (
    <div className="my-2 flex w-full max-w-md items-center gap-3 rounded-lg border border-line bg-bg-2 py-2 pr-1.5 pl-2.5">
      <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-accent-soft text-accent">
        {ready ? <Icon size={18} /> : <LoaderCircle size={17} className="spin" />}
      </span>
      <button
        type="button"
        disabled={!ready}
        onClick={() => void openFile(path)}
        aria-label={`Ouvrir ${shown}`}
        title={ready ? `Ouvrir ${shown}` : undefined}
        className="group min-w-0 flex-1 text-left"
      >
        <span className="block truncate text-sm font-medium text-fg group-enabled:group-hover:underline">
          {shown}
        </span>
        <span className="block truncate text-xs text-fg-3">{formatLabel(shown)}</span>
      </button>
      {ready ? (
        <div className="flex shrink-0 items-center">
          {onPreview ? (
            <IconButton label="Aperçu" size="sm" onClick={onPreview}>
              <Eye size={15} />
            </IconButton>
          ) : null}
          <IconButton
            label="Télécharger (dossier Téléchargements)"
            size="sm"
            onClick={() => void saveToDownloads(path)}
          >
            <Download size={15} />
          </IconButton>
          <IconButton
            label="Afficher dans l’Explorateur"
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

/** Image générée : aperçu (420 px de large au plus, comme Tk), clic pour l'agrandir */
export function GeneratedImage({ path }: { path: string }) {
  const url = useFileUrl(path);
  const [open, setOpen] = useState(false);
  const name = baseName(path);
  return (
    <figure className="my-2">
      <button
        type="button"
        onClick={() => setOpen(true)}
        aria-label={`Agrandir ${name}`}
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
      <figcaption className="mt-1 text-xs text-fg-3">{name} — clic pour agrandir</figcaption>
      <Lightbox open={open} onOpenChange={setOpen} url={url} path={path} name={name} generated />
    </figure>
  );
}
