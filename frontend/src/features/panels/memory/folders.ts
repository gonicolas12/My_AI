/*
 * Dossier déposé sur l'onglet Documents de la Mémoire : ses fichiers lus dans
 * la page (entrées FileSystem de Chromium et de WebView2), chacun avec son
 * chemin dans le dossier. adding.ts les envoie ensemble ; le serveur les range
 * sous le nom du dossier (POST /api/memory/documents/folder), que l'onglet
 * montre comme un dossier à déplier.
 *
 * Comme l'indexation des dossiers (core/folder_indexer.py) : ni fichiers ni
 * dossiers cachés, ni dossiers de dépendances ou de build (node_modules, .git,
 * dist…). Seuls partent les formats que la Mémoire sait lire.
 */

import { ACCEPT, ACCEPT_ALL } from '../../chat/attach';

/** Fichiers d'un dossier, au plus (FOLDER_FILES_MAX du serveur) */
export const FOLDER_FILES_MAX = 200;
/** Entrées parcourues, au plus : un dossier énorme s'arrête là */
const ENTRIES_MAX = 20_000;
/** Fichier envoyé, au plus (limite du serveur) ; un texte ou du code, 2 Mo (folder_indexer) */
const FILE_BYTES_MAX = 50 * 1024 * 1024;
const TEXT_BYTES_MAX = 2 * 1024 * 1024;

/** Dossiers jamais parcourus (core/folder_indexer._DEFAULT_EXCLUDE_DIRS) */
// prettier-ignore
const EXCLUDED_DIRS = new Set([
  '.git', '.svn', '.hg', '.bzr',
  'node_modules', 'bower_components', 'jspm_packages',
  '__pycache__', '.mypy_cache', '.pytest_cache', '.ruff_cache', '.tox',
  '.venv', 'venv', 'env', '.env', 'virtualenv',
  'dist', 'build', 'out', 'target', 'bin', 'obj',
  '.idea', '.vscode', '.vs',
  '.next', '.nuxt', '.svelte-kit', '.cache', '.parcel-cache',
  'coverage', '.nyc_output', 'site-packages', '__MACOSX',
  '.gradle', '.terraform', 'vendor',
]);

const SUPPORTED = new Set(ACCEPT_ALL.split(','));
const TEXT = new Set(ACCEPT.Code.split(','));

function extension(name: string): string {
  const dot = name.lastIndexOf('.');
  return dot > 0 ? name.slice(dot).toLowerCase() : '';
}

export interface FolderFile {
  file: File;
  /** Chemin dans le dossier déposé : « src/app.py » */
  path: string;
}

export interface ReadFolder {
  name: string;
  files: FolderFile[];
  /** Fichiers laissés de côté : format non pris en charge, trop lourds */
  skipped: number;
  /** Plus de FOLDER_FILES_MAX fichiers à lire (ou d'ENTRIES_MAX entrées) : rien ne part */
  tooBig: boolean;
}

/** Toutes les entrées d'un dossier : readEntries les rend par lots, jusqu'à un lot vide */
function entriesOf(directory: FileSystemDirectoryEntry): Promise<FileSystemEntry[]> {
  const reader = directory.createReader();
  const entries: FileSystemEntry[] = [];
  return new Promise((resolve, reject) => {
    const next = () => {
      reader.readEntries((batch) => {
        if (!batch.length) {
          resolve(entries);
          return;
        }
        entries.push(...batch);
        next();
      }, reject);
    };
    next();
  });
}

function fileOf(entry: FileSystemFileEntry): Promise<File> {
  return new Promise((resolve, reject) => {
    entry.file(resolve, reject);
  });
}

const isDirectory = (entry: FileSystemEntry): entry is FileSystemDirectoryEntry =>
  entry.isDirectory;
const isFile = (entry: FileSystemEntry): entry is FileSystemFileEntry => entry.isFile;

/** Fichiers à mettre en mémoire d'un dossier déposé, dans l'ordre alphabétique */
export async function readFolder(root: FileSystemDirectoryEntry): Promise<ReadFolder> {
  const read: ReadFolder = { name: root.name, files: [], skipped: 0, tooBig: false };
  let visited = 0;
  const walk = async (directory: FileSystemDirectoryEntry, prefix: string): Promise<void> => {
    const entries = await entriesOf(directory);
    entries.sort((a, b) => a.name.localeCompare(b.name));
    for (const entry of entries) {
      if (read.tooBig) return;
      visited += 1;
      if (visited > ENTRIES_MAX) {
        read.tooBig = true;
        return;
      }
      if (entry.name.startsWith('.')) continue;
      if (isDirectory(entry)) {
        if (!EXCLUDED_DIRS.has(entry.name)) await walk(entry, `${prefix}${entry.name}/`);
        continue;
      }
      if (!isFile(entry)) continue;
      const ext = extension(entry.name);
      if (!SUPPORTED.has(ext)) {
        read.skipped += 1;
        continue;
      }
      const file = await fileOf(entry);
      if (file.size > (TEXT.has(ext) ? TEXT_BYTES_MAX : FILE_BYTES_MAX)) {
        read.skipped += 1;
        continue;
      }
      if (read.files.length >= FOLDER_FILES_MAX) {
        read.tooBig = true;
        return;
      }
      read.files.push({ file, path: `${prefix}${entry.name}` });
    }
  };
  await walk(root, '');
  return read;
}
