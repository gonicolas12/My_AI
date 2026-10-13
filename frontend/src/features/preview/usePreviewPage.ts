/*
 * Page d'aperçu d'un artefact : créée par le serveur à la première ouverture
 * (interfaces/desktop/previews.py), puis gardée tant que l'appli tourne.
 */

import { useEffect, useState } from 'react';

import { api, type PreviewView } from '../../lib/api';
import { type Artifact, artifactKey } from '../../lib/artifacts';

const pages = new Map<string, PreviewView>();

function createPage(artifact: Artifact): Promise<PreviewView> {
  if (artifact.kind === 'document') return api.documentPreview(artifact.path);
  return api.artifactPreview({
    code: artifact.code,
    kind: artifact.kind,
    title: artifact.title,
    language: artifact.language,
    index: artifact.index,
  });
}

export interface PreviewPage {
  view: PreviewView | null;
  error: string | null;
}

export function usePreviewPage(artifact: Artifact | undefined): PreviewPage {
  const key = artifact ? artifactKey(artifact) : null;
  const [result, setResult] = useState<{ key: string; page: PreviewPage } | null>(null);

  useEffect(() => {
    if (!artifact || !key || pages.has(key)) return undefined;
    let alive = true;
    createPage(artifact)
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
  }, [artifact, key]);

  if (!key) return { view: null, error: null };
  const cached = pages.get(key);
  if (cached) return { view: cached, error: null };
  return result?.key === key ? result.page : { view: null, error: null };
}
