/*
 * Pont entre l'interface et la fenêtre qui l'affiche.
 *
 * L'interface ne parle à la fenêtre qu'à travers ce module : dans la fenêtre
 * pywebview, il appelle les fonctions de interfaces/desktop/shell_api.py
 * (window.pywebview.api) ; dans un navigateur (repli sans pywebview, mode
 * --headless), il fait au mieux avec les API du navigateur. Passer à Electron
 * ne demandera de changer que ce fichier.
 */

interface PywebviewApi {
  open_external(url: string): Promise<boolean>;
  platform(): Promise<string>;
  set_title_bar_colors(background: string, text: string): Promise<boolean>;
  pick_files(kind: string): Promise<string[] | null>;
  pick_folder(): Promise<string | null>;
  pick_workflow(): Promise<string | null>;
  save_file(name: string, fmt: string): Promise<string | null>;
  native_preview_available(): Promise<boolean>;
  native_preview_show(previewId: string, rect: DeviceRect): Promise<boolean>;
  native_preview_place(rect: DeviceRect, visible: boolean): Promise<boolean>;
  native_preview_close(): Promise<boolean>;
}

/** Rectangle en pixels de l'écran, dans la zone client de la fenêtre */
export interface DeviceRect {
  x: number;
  y: number;
  width: number;
  height: number;
}

/** Entrées du menu « + » : types de pièces jointes de l'interface Tk */
export type AttachKind = 'PDF' | 'DOCX' | 'Excel' | 'PowerPoint' | 'Code' | 'Image';

declare global {
  interface Window {
    pywebview?: { api?: Partial<PywebviewApi> };
  }
}

/** Schémas qu'un lien peut ouvrir hors de l'appli (navigateur, messagerie) */
const EXTERNAL_SCHEMES = new Set(['http:', 'https:', 'mailto:']);

/** URL absolue d'un lien externe autorisé, ou null (javascript:, file:…) */
export function externalUrl(href: string): string | null {
  let url: URL;
  try {
    url = new URL(href, window.location.href);
  } catch {
    return null;
  }
  if (!EXTERNAL_SCHEMES.has(url.protocol)) return null;
  if (url.origin === window.location.origin) return null;
  return url.href;
}

function api(): Partial<PywebviewApi> | undefined {
  return window.pywebview?.api;
}

/** Attend le pont de pywebview (injecté après le chargement de la page) */
function whenBridgeReady(callback: () => void): () => void {
  if (api()?.open_external) {
    callback();
    return () => undefined;
  }
  const onReady = () => callback();
  window.addEventListener('pywebviewready', onReady, { once: true });
  return () => window.removeEventListener('pywebviewready', onReady);
}

/** Couleur CSS calculée (« rgb(15, 15, 15) ») → « #0f0f0f » ; null si illisible */
export function cssColorToHex(value: string): string | null {
  const match = /^rgba?\((\d+),\s*(\d+),\s*(\d+)/.exec(value.trim());
  if (!match) return /^#[0-9a-f]{6}$/i.test(value.trim()) ? value.trim().toLowerCase() : null;
  return `#${match
    .slice(1, 4)
    .map((part) => Number(part).toString(16).padStart(2, '0'))
    .join('')}`;
}

/** Valeur d'un jeton de couleur de tokens.css, en « #rrggbb » */
function tokenColor(name: string): string | null {
  const probe = document.createElement('span');
  probe.style.color = `var(${name})`;
  probe.style.display = 'none';
  document.body.appendChild(probe);
  const color = getComputedStyle(probe).color;
  probe.remove();
  return cssColorToHex(color);
}

let nativeAvailable: Promise<boolean> | null = null;

export const shell = {
  /** Vrai dans la fenêtre pywebview (une fois son pont injecté) */
  isDesktop(): boolean {
    return Boolean(api()?.open_external);
  },

  /** Dialogues de fichiers du système : dans la fenêtre pywebview seulement */
  canPickFiles(): boolean {
    return Boolean(api()?.pick_files);
  },

  /** Fichiers à joindre (dialogue du système) ; liste vide si annulé */
  async pickFiles(kind: AttachKind): Promise<string[]> {
    const pick = api()?.pick_files;
    if (!pick) return [];
    try {
      return (await pick(kind)) ?? [];
    } catch {
      return [];
    }
  },

  /** Dossier à attacher au projet (dialogue du système) */
  async pickFolder(): Promise<string | null> {
    const pick = api()?.pick_folder;
    if (!pick) return null;
    try {
      return await pick();
    } catch {
      return null;
    }
  },

  /** Workflow enregistré à charger sur le canvas des agents (dialogue du système) */
  async pickWorkflow(): Promise<string | null> {
    const pick = api()?.pick_workflow;
    if (!pick) return null;
    try {
      return await pick();
    } catch {
      return null;
    }
  },

  /** Chemin d'enregistrement d'un export ou d'un workflow (dialogue du système) */
  async saveFile(name: string, fmt: string): Promise<string | null> {
    const save = api()?.save_file;
    if (!save) return null;
    try {
      return await save(name, fmt);
    } catch {
      return null;
    }
  },

  /**
   * Visionneuses Office de Windows dans le volet d'aperçu (fenêtre pywebview,
   * interfaces/desktop/native_viewer.py). La visionneuse est une fenêtre enfant
   * posée au-dessus de la page : la page la masque sous ses dialogues, menus et
   * notifications (nativeLayer.ts).
   */
  nativePreview: {
    available(): Promise<boolean> {
      const check = api()?.native_preview_available;
      if (!check) return Promise.resolve(false);
      nativeAvailable ??= check().then(Boolean, () => false);
      return nativeAvailable;
    },
    /** Charge l'aperçu (masqué) à la place donnée ; vrai quand la visionneuse est prête */
    async show(previewId: string, rect: DeviceRect): Promise<boolean> {
      const show = api()?.native_preview_show;
      if (!show) return false;
      try {
        return Boolean(await show(previewId, rect));
      } catch {
        return false;
      }
    },
    place(rect: DeviceRect, visible: boolean): void {
      void api()
        ?.native_preview_place?.(rect, visible)
        .catch(() => false);
    },
    close(): void {
      void api()
        ?.native_preview_close?.()
        .catch(() => false);
    },
  },

  /** Ouvre un lien dans le navigateur du système ; la fenêtre ne le charge jamais. */
  async openExternal(href: string): Promise<boolean> {
    const url = externalUrl(href);
    if (!url) return false;
    const openExternal = api()?.open_external;
    if (openExternal) {
      try {
        return await openExternal(url);
      } catch {
        return false;
      }
    }
    // Dans pywebview avant l'injection du pont, window.open passe aussi par le
    // navigateur du système (NewWindowRequested, cf. window.py)
    window.open(url, '_blank', 'noopener,noreferrer');
    return true;
  },

  /**
   * Barre de titre de la fenêtre aux couleurs de la page (Windows 11) : elles
   * viennent de tokens.css, seul fichier à changer pour un autre thème.
   */
  syncTitleBar(): () => void {
    return whenBridgeReady(() => {
      const background = tokenColor('--bg-primary');
      const text = tokenColor('--text-primary');
      const setColors = api()?.set_title_bar_colors;
      if (background && text && setColors) void setColors(background, text).catch(() => false);
    });
  },
};

/**
 * Empêche la fenêtre de quitter l'appli : tout lien externe s'ouvre dans le
 * navigateur du système, et un fichier déposé hors d'une zone prévue n'est
 * jamais ouvert par la page. Renvoie la fonction de retrait des écouteurs.
 */
export function installNavigationGuard(): () => void {
  const onClick = (event: MouseEvent) => {
    if (event.defaultPrevented) return;
    const target = event.target instanceof Element ? event.target : null;
    const anchor = target?.closest('a[href]');
    if (!(anchor instanceof HTMLAnchorElement)) return;
    const href = anchor.getAttribute('href') ?? '';
    if (href.startsWith('#')) return;
    event.preventDefault();
    if (event.type === 'click' || event.button === 1) void shell.openExternal(anchor.href);
  };
  const onDragOver = (event: DragEvent) => {
    if (!event.defaultPrevented) {
      event.preventDefault();
      if (event.dataTransfer) event.dataTransfer.dropEffect = 'none';
    }
  };
  const onDrop = (event: DragEvent) => {
    if (!event.defaultPrevented) event.preventDefault();
  };
  document.addEventListener('click', onClick);
  document.addEventListener('auxclick', onClick);
  document.addEventListener('dragover', onDragOver);
  document.addEventListener('drop', onDrop);
  return () => {
    document.removeEventListener('click', onClick);
    document.removeEventListener('auxclick', onClick);
    document.removeEventListener('dragover', onDragOver);
    document.removeEventListener('drop', onDrop);
  };
}
