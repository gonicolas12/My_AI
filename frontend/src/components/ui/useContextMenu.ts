import { type MouseEvent, useCallback, useRef, useState } from 'react';

/** Point de la fenêtre où ouvrir un menu de clic droit (ContextMenu de Menu.tsx) */
export interface MenuPoint {
  x: number;
  y: number;
}

/**
 * Clic droit (ou touche Menu) sur un élément : où ouvrir son menu, et l'élément
 * à qui rendre le focus ensuite. La fenêtre n'a pas de menu par défaut : pywebview
 * coupe celui de WebView2 hors du mode debug.
 */
export function useContextMenu() {
  const [at, setAt] = useState<MenuPoint | null>(null);
  const origin = useRef<HTMLElement | null>(null);
  const open = useCallback((event: MouseEvent<HTMLElement>) => {
    event.preventDefault();
    event.stopPropagation();
    origin.current = event.currentTarget;
    if (event.clientX || event.clientY) {
      setAt({ x: event.clientX, y: event.clientY });
    } else {
      // Touche Menu, Maj+F10 : pas de pointeur, le menu sous l'élément
      const box = event.currentTarget.getBoundingClientRect();
      setAt({ x: box.left, y: box.bottom });
    }
  }, []);
  const close = useCallback(() => setAt(null), []);
  return { at, open, close, origin };
}
