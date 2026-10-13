/*
 * Fichiers locaux montrés par la fenêtre (images, PDF, vignettes).
 *
 * La page ne lit jamais le disque elle-même : le serveur signe un lien pour
 * chaque fichier qu'il connaît (pièce jointe, document ou image produits),
 * cf. interfaces/desktop/files.py. Les demandes d'une même image sont
 * regroupées en une seule requête, et les liens obtenus gardés.
 */

import { useEffect, useState } from 'react';

import { api } from './api';

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

/** Lien d'un fichier pour l'affichage (null tant qu'il n'est pas connu) */
export function useFileUrl(path: string | null | undefined): string | null {
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
  if (!path) return null;
  if (resolved?.path === path) return resolved.url;
  return links.get(path) ?? null;
}

/** Réservé aux tests */
export function resetFileLinks(): void {
  links.clear();
  waiting.clear();
  batch = [];
  if (timer) clearTimeout(timer);
  timer = null;
}
