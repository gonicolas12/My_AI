import type { MessageKey } from '../i18n';

/** Système de la machine : la fenêtre et son serveur local tournent sur la même */
export type Platform = 'windows' | 'mac' | 'linux';

/**
 * D'après l'agent de la page : WebView2 sous Windows, WKWebView sous macOS,
 * WebKitGTK ou Qt sous Linux. Inconnu : Windows, celui de la plupart.
 */
export function platform(agent: string = globalThis.navigator?.userAgent ?? ''): Platform {
  if (/Windows/i.test(agent)) return 'windows';
  if (/Macintosh|Mac OS X/i.test(agent)) return 'mac';
  if (/Linux|X11|CrOS/i.test(agent)) return 'linux';
  return 'windows';
}

const REVEAL: Record<Platform, { file: MessageKey; path: MessageKey }> = {
  windows: { file: 'chat.file.reveal', path: 'chat.path.reveal' },
  mac: { file: 'chat.file.revealMac', path: 'chat.path.revealMac' },
  linux: { file: 'chat.file.revealLinux', path: 'chat.path.revealLinux' },
};

/**
 * « Afficher dans l'Explorateur », « … le Finder », « … le gestionnaire de
 * fichiers » : le bouton (file) et l'infobulle d'un chemin (path, avec {path})
 */
export function revealLabels(): { file: MessageKey; path: MessageKey } {
  return REVEAL[platform()];
}
