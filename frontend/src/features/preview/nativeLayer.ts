/*
 * Visionneuse Office et couches de la page : la visionneuse est une fenêtre
 * enfant posée au-dessus de WebView2 (native_viewer.py), la page ne peut rien
 * dessiner par-dessus. Elle se masque donc dès qu'un dialogue, un panneau ou la
 * palette s'ouvre par-dessus elle (leur voile couvre la fenêtre), ou qu'un menu,
 * une infobulle, une liste ou un toast passe sur sa place. Le dialogue qui la
 * contient (fenêtre d'aperçu d'une pièce jointe, panneau Mémoire) ne compte
 * pas, ni ceux qu'il recouvre.
 *
 * Il n'y a qu'une visionneuse : deux aperçus Office ouverts à la fois (volet
 * de droite, puis panneau Mémoire) se la passent. Le dernier ouvert la prend,
 * le précédent la retrouve à sa fermeture (claimNative).
 */

import { type DeviceRect, shell } from '../../lib/shell';

/** Dialogues modaux : panneaux, confirmations, palette, image en grand */
const MODALS = '[role="dialog"], [role="alertdialog"]';

/** Couches flottantes, masquantes seulement si elles touchent la visionneuse */
const FLOATING = [
  '[data-radix-popper-content-wrapper]',
  '[data-toast-region] > *',
  '[role="menu"]',
  '[role="listbox"]',
].join(', ');

const overlap = (a: DOMRect, b: DOMRect) =>
  a.width > 0 &&
  a.height > 0 &&
  a.left < b.right &&
  a.right > b.left &&
  a.top < b.bottom &&
  a.bottom > b.top;

/** Le dialogue `modal` passe-t-il sous celui qui contient la visionneuse ? */
function below(modal: Element, own: Element): boolean {
  return Boolean(own.compareDocumentPosition(modal) & Node.DOCUMENT_POSITION_PRECEDING);
}

/**
 * Vrai si une couche de la page passerait sous la visionneuse posée sur `slot`
 *
 * @param element place de la visionneuse : le dialogue qui la contient ne la couvre pas
 */
export function coversNative(
  slot: DOMRect,
  root: ParentNode = document,
  element: Element | null = null,
): boolean {
  const modals = Array.from(root.querySelectorAll(MODALS));
  // Dialogue de la visionneuse : le plus proche d'elle qui la contient
  const own = element ? element.closest(MODALS) : null;
  const covering = modals.some(
    (modal) => !(element && modal.contains(element)) && !(own && below(modal, own)),
  );
  if (covering) return true;
  return Array.from(root.querySelectorAll(FLOATING)).some((layer) => {
    // Menu ou infobulle d'un dialogue que la visionneuse recouvre : sous elle
    if (own && !own.contains(layer) && below(layer, own)) return false;
    return overlap(layer.getBoundingClientRect(), slot);
  });
}

/** Rectangle CSS → pixels de l'écran (échelle de l'écran et zoom de la page compris) */
export function deviceRect(rect: DOMRect, ratio = window.devicePixelRatio || 1): DeviceRect {
  const x = Math.round(rect.left * ratio);
  const y = Math.round(rect.top * ratio);
  return {
    x,
    y,
    width: Math.max(1, Math.round(rect.right * ratio) - x),
    height: Math.max(1, Math.round(rect.bottom * ratio) - y),
  };
}

/** Application ouverte par la visionneuse, pour « Ouverture de l'aperçu Word… » (Tk) */
export function nativeAppLabel(path: string): string {
  const extension = /\.[^./\\]+$/.exec(path)?.[0].toLowerCase() ?? '';
  if (['.docx', '.doc'].includes(extension)) return 'Word';
  if (['.pptx', '.ppt'].includes(extension)) return 'PowerPoint';
  if (['.xlsx', '.xlsm', '.xls'].includes(extension)) return 'Excel';
  return '';
}

// ── Une seule visionneuse pour plusieurs aperçus ───────────────────────────

export interface NativeClaim {
  /** Visionneuse rendue : l'aperçu recharge son document */
  resume: () => void;
  /** Visionneuse prise par un aperçu ouvert depuis : l'aperçu attend */
  suspend: () => void;
}

export interface NativeHandle {
  /** Cet aperçu tient la visionneuse (le dernier ouvert) */
  owns: () => boolean;
  /** Aperçu fermé : le précédent reprend la visionneuse, sinon elle se ferme */
  release: () => void;
}

const claims: NativeClaim[] = [];

/** Un aperçu Office demande la visionneuse ; le précédent la lui cède */
export function claimNative(claim: NativeClaim): NativeHandle {
  const previous = claims.at(-1);
  claims.push(claim);
  previous?.suspend();
  return {
    owns: () => claims.at(-1) === claim,
    release: () => {
      const index = claims.indexOf(claim);
      if (index < 0) return;
      const owner = index === claims.length - 1;
      claims.splice(index, 1);
      if (!owner) return;
      const next = claims.at(-1);
      if (next) next.resume();
      else shell.nativePreview.close();
    },
  };
}

/** Réservé aux tests */
export function resetNativeClaims(): void {
  claims.length = 0;
}
