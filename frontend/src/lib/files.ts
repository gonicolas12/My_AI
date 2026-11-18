/*
 * Fichiers locaux montrés par la fenêtre (images, PDF, vignettes).
 *
 * La page ne lit jamais le disque elle-même : le serveur signe un lien pour
 * chaque fichier qu'il connaît (pièce jointe, document ou image produits),
 * cf. interfaces/desktop/files.py. Les demandes d'une même image sont
 * regroupées en une seule requête, et les liens obtenus gardés.
 */

import { useEffect, useRef, useState } from 'react';

import { ApiError, api, type FileInfo, type FileText } from './api';

const links = new Map<string, string>();
const waiting = new Map<string, ((url: string | null) => void)[]>();
let batch: string[] = [];
let timer: ReturnType<typeof setTimeout> | null = null;

function settle(path: string, url: string | null): void {
  // Un refus n'est pas gardé : le fichier peut devenir connu plus tard
  if (url) links.set(path, url);
  const callbacks = waiting.get(path) ?? [];
  waiting.delete(path);
  for (const callback of callbacks) callback(url);
}

function flush(): void {
  timer = null;
  const paths = batch;
  batch = [];
  api
    .fileLinks(paths)
    .then((result) => {
      for (const path of paths) settle(path, result.links[path] ?? null);
    })
    .catch(() => {
      for (const path of paths) settle(path, null);
    });
}

/** Lien signé d'un fichier local, ou null s'il est inconnu du serveur */
export function fileUrl(path: string): Promise<string | null> {
  const known = links.get(path);
  if (known) return Promise.resolve(known);
  return new Promise((resolve) => {
    const callbacks = waiting.get(path);
    if (callbacks) {
      callbacks.push(resolve);
      return;
    }
    waiting.set(path, [resolve]);
    batch.push(path);
    timer ??= setTimeout(flush, 16);
  });
}

export interface FileLink {
  /** Lien signé, ou null (pas encore connu, ou refusé) */
  url: string | null;
  /** Réponse du serveur reçue : url null veut alors dire refusé */
  settled: boolean;
}

/** Lien d'un fichier pour l'affichage, et si le serveur a répondu */
export function useFileLink(path: string | null | undefined): FileLink {
  const [resolved, setResolved] = useState<{ path: string; url: string | null } | null>(null);
  useEffect(() => {
    if (!path) return undefined;
    let alive = true;
    void fileUrl(path).then((url) => {
      if (alive) setResolved({ path, url });
    });
    return () => {
      alive = false;
    };
  }, [path]);
  if (!path) return { url: null, settled: true };
  if (resolved?.path === path) return { url: resolved.url, settled: true };
  const known = links.get(path) ?? null;
  return { url: known, settled: known !== null };
}

/** Lien d'un fichier pour l'affichage (null tant qu'il n'est pas connu) */
export function useFileUrl(path: string | null | undefined): string | null {
  return useFileLink(path).url;
}

export interface Loaded<T> {
  data: T | null;
  error: string | null;
  /** Code HTTP du refus (415 : fichier binaire) */
  status: number | null;
}

/**
 * Lecture d'une ressource d'un fichier (texte, taille…) tant que le composant
 * l'affiche : relue à chaque ouverture, un fichier peut avoir changé depuis
 */
export function useLoaded<T>(key: string | null, load: (key: string) => Promise<T>): Loaded<T> {
  const [result, setResult] = useState<{ key: string; value: Loaded<T> } | null>(null);
  const loader = useRef(load);
  useEffect(() => {
    loader.current = load;
  });
  useEffect(() => {
    if (!key) return undefined;
    let alive = true;
    // Une erreur levée d'emblée devient un refus, comme une réponse du serveur
    Promise.resolve(key)
      .then(loader.current)
      .then(
        (data) => {
          if (alive) setResult({ key, value: { data, error: null, status: null } });
        },
        (error: unknown) => {
          if (!alive) return;
          const message = error instanceof Error ? error.message : String(error);
          const status = error instanceof ApiError ? error.status : null;
          setResult({ key, value: { data: null, error: message, status } });
        },
      );
    return () => {
      alive = false;
    };
  }, [key]);
  if (!key || result?.key !== key) return { data: null, error: null, status: null };
  return result.value;
}

/** Début d'un fichier texte (code, Markdown…) ; status 415 pour un fichier binaire */
export function useFileText(path: string | null): Loaded<FileText> {
  return useLoaded(path, (key) => api.fileText(key));
}

/** Taille et date d'un fichier, pour l'en-tête de son aperçu */
export function useFileInfo(path: string | null): Loaded<FileInfo> {
  return useLoaded(path, (key) => api.fileInfo(key));
}

// ── Images d'un fichier Markdown en aperçu ─────────────────────────────────

/** Adresse avec un schéma (https:, data:, C:…) ou absolue : pas une image du dossier */
const NOT_RELATIVE = /^(?:[a-z][a-z0-9+.-]*:|[\\/])/i;

/** Chemin d'une image relative d'un fichier Markdown (« docs/a.png »), à côté de lui ; null sinon */
export function relativeImagePath(file: string, src: string): string | null {
  const clean = src.split(/[?#]/)[0] ?? '';
  if (!clean || NOT_RELATIVE.test(clean)) return null;
  let decoded = clean;
  try {
    decoded = decodeURIComponent(clean);
  } catch {
    // « % » isolé : le chemin tel quel
  }
  const folder = file.replace(/[\\/][^\\/]*$/, '');
  const separator = file.includes('\\') ? '\\' : '/';
  return `${folder}${separator}${decoded.replace(/^\.[\\/]/, '').replace(/[\\/]/g, separator)}`;
}

const markdownImages = new Map<string, string | null>();

/**
 * Lien signé d'une image rangée dans le dossier d'un fichier Markdown affiché
 * (logo d'un README) : le serveur ne le signe que pour une image de ce dossier,
 * et seulement si le fichier Markdown lui-même peut s'afficher
 */
export function useMarkdownImage(file: string, path: string): string | null {
  const key = `${file}\n${path}`;
  const [resolved, setResolved] = useState<{ key: string; url: string | null } | null>(null);
  useEffect(() => {
    if (markdownImages.has(key)) return undefined;
    let alive = true;
    api.fileLinks([path], file).then(
      (result) => {
        const url = result.links[path] ?? null;
        if (url) markdownImages.set(key, url);
        if (alive) setResolved({ key, url });
      },
      () => {
        if (alive) setResolved({ key, url: null });
      },
    );
    return () => {
      alive = false;
    };
  }, [key, file, path]);
  if (markdownImages.has(key)) return markdownImages.get(key) ?? null;
  return resolved?.key === key ? resolved.url : null;
}

/** Réservé aux tests */
export function resetFileLinks(): void {
  markdownImages.clear();
  links.clear();
  waiting.clear();
  batch = [];
  if (timer) clearTimeout(timer);
  timer = null;
}
