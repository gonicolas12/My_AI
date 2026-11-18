/*
 * Aperçu d'un fichier selon son format (volet de droite, fenêtre des pièces
 * jointes, volet de la Mémoire) :
 *  - image, audio, vidéo : affichés par la fenêtre, par leur lien signé ;
 *  - PDF, Word, Excel, PowerPoint, CSV : page d'aperçu du serveur (lecteur PDF
 *    de WebView2, visionneuses de Windows, ou page HTML), comme avant ;
 *  - Markdown, HTML, SVG : rendus, avec leur source en second onglet ;
 *  - code et texte : lus par le serveur (début du fichier), colorés ;
 *  - le reste : lu comme du texte s'il en est, « pas d'aperçu » sinon.
 */

import { extensionOf } from './artifacts';

export type FileKind =
  | 'image'
  | 'svg'
  | 'audio'
  | 'video'
  | 'pdf'
  | 'office'
  | 'table'
  | 'markdown'
  | 'html'
  | 'code'
  | 'text'
  | 'other';

const IMAGES = new Set(['.png', '.jpg', '.jpeg', '.gif', '.webp', '.bmp', '.ico', '.avif']);
const AUDIO = new Set(['.mp3', '.wav', '.ogg', '.oga', '.m4a', '.aac', '.flac', '.opus']);
const VIDEO = new Set(['.mp4', '.webm', '.mov', '.m4v', '.ogv']);
/** Visionneuses de Windows, sinon page HTML du serveur (document_preview.py) */
const OFFICE = new Set(['.docx', '.doc', '.xlsx', '.xlsm', '.xls', '.pptx', '.potx', '.ppt']);
const MARKDOWN = new Set(['.md', '.markdown', '.mdx']);
const HTML = new Set(['.html', '.htm', '.xhtml']);
const TEXT = new Set(['.txt', '.log', '.rst', '.text', '.tsv', '.out', '.err']);

/** Extension → langage de la coloration (languages.ts) ; sans entrée : texte brut */
const CODE: Record<string, string> = {
  '.py': 'python',
  '.pyw': 'python',
  '.pyi': 'python',
  '.ipynb': 'json',
  '.js': 'javascript',
  '.mjs': 'javascript',
  '.cjs': 'javascript',
  '.jsx': 'jsx',
  '.ts': 'typescript',
  '.mts': 'typescript',
  '.cts': 'typescript',
  '.tsx': 'tsx',
  '.json': 'json',
  '.jsonc': 'jsonc',
  '.json5': 'jsonc',
  '.yaml': 'yaml',
  '.yml': 'yaml',
  '.toml': 'toml',
  '.ini': 'ini',
  '.cfg': 'ini',
  '.conf': 'ini',
  '.properties': 'ini',
  '.env': 'ini',
  '.xml': 'xml',
  '.xsd': 'xml',
  '.xsl': 'xml',
  '.csproj': 'xml',
  '.css': 'css',
  '.scss': 'scss',
  '.sass': 'scss',
  '.less': 'css',
  '.sql': 'sql',
  '.sh': 'shellscript',
  '.bash': 'shellscript',
  '.zsh': 'shellscript',
  '.ps1': 'powershell',
  '.psm1': 'powershell',
  '.bat': 'bat',
  '.cmd': 'bat',
  '.c': 'c',
  '.h': 'c',
  '.cpp': 'cpp',
  '.cc': 'cpp',
  '.cxx': 'cpp',
  '.hpp': 'cpp',
  '.hh': 'cpp',
  '.cs': 'csharp',
  '.java': 'java',
  '.kt': 'kotlin',
  '.kts': 'kotlin',
  '.go': 'go',
  '.rs': 'rust',
  '.rb': 'ruby',
  '.php': 'php',
  '.pl': 'perl',
  '.pm': 'perl',
  '.lua': 'lua',
  '.r': 'r',
  '.swift': 'swift',
  '.scala': 'scala',
  '.dart': 'dart',
  '.hs': 'haskell',
  '.m': 'matlab',
  '.tex': 'latex',
  '.graphql': 'graphql',
  '.gql': 'graphql',
  '.diff': 'diff',
  '.patch': 'diff',
  '.vue': 'html',
  '.svelte': 'html',
  '.gradle': 'kotlin',
  '.dockerfile': 'dockerfile',
  '.mk': 'makefile',
};

/** Fichiers sans extension connus par leur nom */
const NAMED: Record<string, string> = {
  dockerfile: 'dockerfile',
  makefile: 'makefile',
  '.gitignore': 'ini',
  '.gitattributes': 'ini',
  '.editorconfig': 'ini',
  '.env': 'ini',
};

function nameOf(path: string): string {
  return (path.split(/[\\/]/).pop() ?? path).toLowerCase();
}

export function fileKind(path: string): FileKind {
  const extension = extensionOf(path);
  if (IMAGES.has(extension)) return 'image';
  if (extension === '.svg') return 'svg';
  if (AUDIO.has(extension)) return 'audio';
  if (VIDEO.has(extension)) return 'video';
  if (extension === '.pdf') return 'pdf';
  if (OFFICE.has(extension)) return 'office';
  if (extension === '.csv') return 'table';
  if (MARKDOWN.has(extension)) return 'markdown';
  if (HTML.has(extension)) return 'html';
  if (extension in CODE || nameOf(path) in NAMED) return 'code';
  if (TEXT.has(extension)) return 'text';
  return 'other';
}

/** Langage de la coloration d'un fichier de code (undefined : texte brut) */
export function codeLanguage(path: string): string | undefined {
  const kind = fileKind(path);
  if (kind === 'markdown') return 'markdown';
  if (kind === 'html') return 'html';
  if (kind === 'svg') return 'xml';
  return CODE[extensionOf(path)] ?? NAMED[nameOf(path)];
}

/** Formats rendus qui ont aussi leur source à montrer (onglets Aperçu et Code) */
export function hasSource(kind: FileKind): boolean {
  return kind === 'markdown' || kind === 'html' || kind === 'svg';
}

/** Formats dont la page d'aperçu vient du serveur (previews.py) */
export function isServerPreview(kind: FileKind): boolean {
  return kind === 'pdf' || kind === 'office' || kind === 'table';
}

/** Formats lus en texte par le serveur (POST /api/files/text) */
export function isTextual(kind: FileKind): boolean {
  return (
    kind === 'markdown' || kind === 'html' || kind === 'code' || kind === 'text' || kind === 'other'
  );
}
