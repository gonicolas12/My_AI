/*
 * Visionneuse Office et couches de la page : la visionneuse est une fenêtre
 * enfant posée au-dessus de WebView2 (native_viewer.py), la page ne peut rien
 * dessiner par-dessus. Elle se masque donc dès qu'un dialogue, un panneau ou la
 * palette s'ouvre (leur voile couvre la fenêtre), ou qu'un menu, une infobulle,
 * une liste ou un toast passe sur sa place.
 */

import type { DeviceRect } from '../../lib/shell';

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

/** Vrai si une couche de la page passerait sous la visionneuse posée sur `slot` */
export function coversNative(slot: DOMRect, root: ParentNode = document): boolean {
  if (root.querySelector(MODALS)) return true;
  return Array.from(root.querySelectorAll(FLOATING)).some((element) =>
    overlap(element.getBoundingClientRect(), slot),
  );
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
