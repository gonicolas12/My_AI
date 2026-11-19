import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterEach } from 'vitest';

// Sans les globales de Vitest, Testing Library ne démonte pas seul le rendu
// d'un test avant le suivant
afterEach(() => {
  cleanup();
});

// Agent de la fenêtre sous Windows : les libellés propres au système
// (« Afficher dans l’Explorateur », lib/platform.ts) ne dépendent pas de la
// machine des tests, que jsdom écrit dans le sien (« (win32) », « (linux) »…)
const WINDOWS_AGENT =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) ' +
  'Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0';
Object.defineProperty(window.navigator, 'userAgent', {
  configurable: true,
  get: () => WINDOWS_AGENT,
});
