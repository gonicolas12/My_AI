/*
 * Page d'aperçu d'un artefact : créée par le serveur à la première ouverture
 * (interfaces/desktop/previews.py), puis gardée tant que l'appli tourne. Dans
 * la fenêtre, Word, Excel et PowerPoint passent par la visionneuse de Windows
 * (aperçu « native ») ; la page HTML n'est produite qu'en repli (fallback).
 *
 * Seuls les blocs HTML/SVG et les documents PDF, Office et CSV en ont une
 * (hasServerPage) : une image, du code ou du Markdown s'affichent dans la page.
 */

import { useCallback, useEffect, useState } from 'react';

import { api, type PreviewView } from '../../lib/api';
import { type Artifact, artifactKey } from '../../lib/artifacts';
import { fileKind, isServerPreview } from '../../lib/fileKinds';
import { shell } from '../../lib/shell';

const pages = new Map<string, PreviewView>();
// Pages demandées, pas encore reçues : une seule demande pour deux affichages (en-tête, corps)
const pending = new Map<string, Promise<PreviewView>>();

async function createPage(artifact: Artifact): Promise<PreviewView> {
  if (artifact.kind === 'document') {
    return api.documentPreview(artifact.path, await shell.nativePreview.available());
  }
  return api.artifactPreview({
    code: artifact.code,
    kind: artifact.kind,
    title: artifact.title,
    language: artifact.language,
    index: artifact.index,
  });
}

function requestPage(key: string, artifact: Artifact): Promise<PreviewView> {
  let request = pending.get(key);
  if (!request) {
    request = createPage(artifact).finally(() => pending.delete(key));
    pending.set(key, request);
  }
  return request;
}

/** L'artefact a-t-il une page d'aperçu du serveur ? */
export function hasServerPage(artifact: Artifact | undefined): artifact is Artifact {
  if (!artifact) return false;
  return artifact.kind !== 'document' || isServerPreview(fileKind(artifact.path));
}

export interface PreviewPage {
  view: PreviewView | null;
  error: string | null;
}

export interface PreviewPageState extends PreviewPage {
  /** Visionneuse native en échec : la page HTML du document, à sa place */
  fallback: () => void;
}

export function usePreviewPage(artifact: Artifact | undefined): PreviewPageState {
  const served = hasServerPage(artifact) ? artifact : undefined;
  const key = served ? artifactKey(served) : null;
  const [result, setResult] = useState<{ key: string; page: PreviewPage } | null>(null);
  const path = served?.kind === 'document' ? served.path : null;

  const fallback = useCallback(() => {
    if (!key || !path) return;
    pages.delete(key);
    setResult({ key, page: { view: null, error: null } });
    api.documentPreview(path, false).then(
      (view) => {
        pages.set(key, view);
        setResult({ key, page: { view, error: null } });
      },
      (error: unknown) => {
        const message = error instanceof Error ? error.message : String(error);
        setResult({ key, page: { view: null, error: message } });
      },
    );
  }, [key, path]);

  useEffect(() => {
    if (!served || !key || pages.has(key)) return undefined;
    let alive = true;
    requestPage(key, served)
      .then((view) => {
        pages.set(key, view);
        if (alive) setResult({ key, page: { view, error: null } });
      })
      .catch((error: unknown) => {
        const message = error instanceof Error ? error.message : String(error);
        if (alive) setResult({ key, page: { view: null, error: message } });
      });
    return () => {
      alive = false;
    };
  }, [served, key]);

  if (!key) return { view: null, error: null, fallback };
  const cached = pages.get(key);
  if (cached) return { view: cached, error: null, fallback };
  return { ...(result?.key === key ? result.page : { view: null, error: null }), fallback };
}
