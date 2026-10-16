/*
 * Artefacts d'une réponse : blocs HTML ou SVG rendables, et documents produits
 * pendant le tour (Word, PDF, Excel…).
 *
 * Miroir de interfaces/artifacts.py (mêmes règles de détection, mêmes titres
 * tirés de <title> puis de <h1>), comme relay/static/app.js côté mobile.
 */

export interface CodeArtifact {
  kind: 'html' | 'svg';
  code: string;
  title: string;
  /** Langage de la fence d'origine (html, svg, xml…) */
  language: string;
  /** Position du bloc parmi les blocs de code de la réponse */
  index: number;
}

export interface DocumentArtifact {
  kind: 'document';
  path: string;
  title: string;
  index: number;
  /** Produit par l'appli (s'ouvre dans son application) ; faux pour une pièce jointe */
  generated: boolean;
}

export type Artifact = CodeArtifact | DocumentArtifact;

const FENCE = /```([\w+#.-]+)?[ \t]*\n?([\s\S]*?)```/g;
const HTML_LANGS = new Set(['html', 'htm', 'xhtml']);
const HTML_HINT = /<!doctype html|<html[\s>]|<body[\s>]|<head[\s>]|<div[\s>]|<table[\s>]/i;
const SVG_HINT = /<svg[\s>]/i;

/** Formats affichés dans le volet (interfaces/document_preview.py, is_previewable) */
const PREVIEWABLE = new Set([
  '.docx',
  '.xlsx',
  '.xlsm',
  '.xls',
  '.csv',
  '.pptx',
  '.potx',
  '.md',
  '.markdown',
  '.txt',
  '.log',
  '.rst',
  '.pdf',
]);

/** 'html', 'svg' ou null selon le langage de la fence et le contenu (_classify) */
function classify(language: string, code: string): 'html' | 'svg' | null {
  const lang = language.toLowerCase();
  const stripped = code.trim();
  if (!stripped) return null;
  if ((lang === 'svg' || SVG_HINT.test(stripped.slice(0, 300))) && SVG_HINT.test(stripped)) {
    return 'svg';
  }
  if (HTML_LANGS.has(lang)) return 'html';
  // Sans langage, ou xml : rendu seulement si ça ressemble à du HTML
  if (HTML_HINT.test(stripped)) return 'html';
  return null;
}

function deriveTitle(code: string, kind: 'html' | 'svg', index: number): string {
  const title = /<title[^>]*>([\s\S]*?)<\/title>/i.exec(code);
  if (title?.[1]?.trim()) return title[1].trim().slice(0, 80);
  const heading = /<h1[^>]*>([\s\S]*?)<\/h1>/i.exec(code);
  if (heading?.[1]) {
    const text = heading[1].replace(/<[^>]+>/g, '').trim();
    if (text) return text.slice(0, 80);
  }
  return `${kind === 'svg' ? 'SVG' : 'Page HTML'} #${index + 1}`;
}

/** Blocs HTML et SVG rendables d'une réponse, dans l'ordre (detect_artifacts) */
export function detectArtifacts(text: string): CodeArtifact[] {
  if (!text || !text.includes('```')) return [];
  const artifacts: CodeArtifact[] = [];
  let index = 0;
  for (const match of text.matchAll(FENCE)) {
    const language = (match[1] ?? '').trim();
    const code = (match[2] ?? '').trim();
    const kind = classify(language, code);
    if (kind) {
      artifacts.push({
        kind,
        code,
        title: deriveTitle(code, kind, artifacts.length),
        language: language.toLowerCase(),
        index,
      });
    }
    index += 1;
  }
  return artifacts;
}

export function extensionOf(path: string): string {
  const name = baseName(path);
  const dot = name.lastIndexOf('.');
  return dot > 0 ? name.slice(dot).toLowerCase() : '';
}

export function baseName(path: string): string {
  return path.split(/[\\/]/).pop() ?? path;
}

export function isPreviewable(path: string): boolean {
  return PREVIEWABLE.has(extensionOf(path));
}

/** Libellé du format d'un fichier (_FORMAT_LABELS de interfaces/document_preview.py) */
const FORMAT_LABELS: Record<string, string> = {
  '.docx': 'Document Word',
  '.doc': 'Document Word',
  '.pdf': 'Document PDF',
  '.pptx': 'Présentation PowerPoint',
  '.potx': 'Modèle PowerPoint',
  '.xlsx': 'Classeur Excel',
  '.xlsm': 'Classeur Excel',
  '.xls': 'Classeur Excel',
  '.csv': 'Données CSV',
  '.md': 'Markdown',
  '.markdown': 'Markdown',
  '.txt': 'Texte',
  '.log': 'Journal',
  '.rst': 'reStructuredText',
  '.html': 'Page HTML',
  '.htm': 'Page HTML',
  '.png': 'Image PNG',
  '.jpg': 'Image JPEG',
  '.jpeg': 'Image JPEG',
  '.webp': 'Image WebP',
  '.gif': 'Image GIF',
};

export function formatLabel(path: string): string {
  const extension = extensionOf(path);
  return FORMAT_LABELS[extension] ?? (extension ? `Fichier ${extension.slice(1)}` : 'Fichier');
}

/** Documents affichables, sans doublon (artifacts_from_documents) */
export function documentArtifacts(
  paths: string[],
  start: number,
  generated = true,
): DocumentArtifact[] {
  const seen = new Set<string>();
  const artifacts: DocumentArtifact[] = [];
  for (const path of paths) {
    const key = path.replace(/\\/g, '/').toLowerCase();
    if (!path || seen.has(key) || !isPreviewable(path)) continue;
    seen.add(key);
    artifacts.push({
      kind: 'document',
      path,
      title: baseName(path),
      index: start + artifacts.length,
      generated,
    });
  }
  return artifacts;
}

/** Tous les artefacts d'une réponse : blocs de code d'abord, puis documents (_collect_artifacts) */
export function messageArtifacts(text: string, documents: string[]): Artifact[] {
  const code = detectArtifacts(text);
  return [...code, ...documentArtifacts(documents, code.length)];
}

/** Identité stable d'un artefact (même aperçu → pas de nouvelle page) */
export function artifactKey(artifact: Artifact): string {
  return artifact.kind === 'document'
    ? `doc:${artifact.path}`
    : `${artifact.kind}:${artifact.index}:${artifact.code.length}:${artifact.code.slice(0, 64)}`;
}
