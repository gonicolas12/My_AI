/*
 * Raccourcis clavier de la fenêtre.
 *
 * WebView2 garde par défaut ceux du navigateur (Ctrl+R et F5 rechargent la
 * page, Ctrl+P imprime, Ctrl+F cherche…) : ils sont neutralisés ici, en plus du
 * réglage de WebView2 (interfaces/desktop/window.py), puis remplacés par ceux
 * de l'appli.
 */

/** Touches Ctrl+… réservées par le navigateur ou par l'appli */
const CTRL_KEYS = new Set([
  'b',
  'd',
  'e',
  'f',
  'g',
  'h',
  'j',
  'k',
  'l',
  'n',
  'o',
  'p',
  'r',
  's',
  't',
  'u',
  ',',
]);

const BROWSER_KEYS = new Set([
  'F3',
  'F5',
  'F7',
  'BrowserBack',
  'BrowserForward',
  'BrowserRefresh',
  'BrowserSearch',
  'BrowserHome',
  'BrowserFavorites',
]);

export function isBrowserShortcut(event: KeyboardEvent): boolean {
  if (BROWSER_KEYS.has(event.key)) return true;
  if (event.altKey && ['ArrowLeft', 'ArrowRight', 'Home'].includes(event.key)) return true;
  const ctrl = event.ctrlKey || event.metaKey;
  return ctrl && !event.altKey && CTRL_KEYS.has(event.key.toLowerCase());
}

/** Combinaison normalisée : « Ctrl+N », « Ctrl+Shift+R », « Escape », « F1 » */
export function comboOf(event: KeyboardEvent): string {
  const parts: string[] = [];
  if (event.ctrlKey || event.metaKey) parts.push('Ctrl');
  if (event.altKey) parts.push('Alt');
  if (event.shiftKey && event.key.length > 1) parts.push('Shift');
  const key = event.key.length === 1 ? event.key.toUpperCase() : event.key;
  parts.push(key);
  return parts.join('+');
}

/** Un dialogue, un menu ou une liste de choix est ouvert : Échap lui revient */
export function overlayOpen(): boolean {
  return (
    document.querySelector(
      '[role="dialog"], [role="alertdialog"], [role="menu"], [role="listbox"]',
    ) !== null
  );
}

export type ShortcutHandlers = Partial<Record<string, (event: KeyboardEvent) => void>>;

export function installShortcuts(handlers: ShortcutHandlers): () => void {
  const onKeyDown = (event: KeyboardEvent) => {
    const handler = handlers[comboOf(event)];
    if (isBrowserShortcut(event) || event.key === 'F1') event.preventDefault();
    if (handler) handler(event);
  };
  // Phase de capture : avant les champs de saisie et le navigateur
  window.addEventListener('keydown', onKeyDown, true);
  return () => window.removeEventListener('keydown', onKeyDown, true);
}
