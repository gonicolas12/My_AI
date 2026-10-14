/*
 * Page d'aperçu d'un artefact : créée par le serveur à la première ouverture
 * (interfaces/desktop/previews.py), puis gardée tant que l'appli tourne. Dans
 * la fenêtre, Word, Excel et PowerPoint passent par la visionneuse de Windows
 * (aperçu « native ») ; la page HTML n'est produite qu'en repli (fallback).
 */

import { useCallback, useEffect, useState } from 'react';

import { api, type PreviewView } from '../../lib/api';
import { type Artifact, artifactKey } from '../../lib/artifacts';
import { shell } from '../../lib/shell';

const pages = new Map<string, PreviewView>();

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

export interface PreviewPage {
  view: PreviewView | null;
  error: string | null;
}

export interface PreviewPageState extends PreviewPage {
  /** Visionneuse native en échec : la page HTML du document, à sa place */
  fallback: () => void;
}

export function usePreviewPage(artifact: Artifact | undefined): PreviewPageState {
  const key = artifact ? artifactKey(artifact) : null;
  const [result, setResult] = useState<{ key: string; page: PreviewPage } | null>(null);
  const path = artifact?.kind === 'document' ? artifact.path : null;

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

  if (!key) return { view: null, error: null, fallback };
  const cached = pages.get(key);
  if (cached) return { view: cached, error: null, fallback };
  return { ...(result?.key === key ? result.page : { view: null, error: null }), fallback };
}
