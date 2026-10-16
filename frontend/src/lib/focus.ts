/*
 * Focus de la fenêtre, signalé au serveur : comme Tk, la fin d'un fil long
 * de la page Agents n'est notifiée par le système que si la fenêtre n'a pas
 * le focus (interfaces/desktop/agents.py).
 */

import { api } from './api';

/** Suit le focus de la fenêtre ; renvoie la fonction qui arrête le suivi */
export function installFocusReport(): () => void {
  let last: boolean | null = null;
  const report = () => {
    // Un clic dans un cadre de la page (artefact) laisse le focus à la fenêtre
    const focused = document.visibilityState === 'visible' && document.hasFocus();
    if (focused === last) return;
    last = focused;
    api.windowFocus(focused).catch(() => {
      last = null; // renvoyé au prochain changement
    });
  };
  window.addEventListener('focus', report);
  window.addEventListener('blur', report);
  document.addEventListener('visibilitychange', report);
  report();
  return () => {
    window.removeEventListener('focus', report);
    window.removeEventListener('blur', report);
    document.removeEventListener('visibilitychange', report);
  };
}
