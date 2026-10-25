import '@fontsource-variable/inter/wght.css';
import '@fontsource-variable/inter/wght-italic.css';
import '@fontsource-variable/jetbrains-mono/wght.css';
import './styles/index.css';

import { Profiler, StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './App';
import { isSupportedLocale, setLocale } from './i18n';
import { api, getToken, initToken } from './lib/api';
import { recordCommit } from './lib/profiling';

initToken();

/** Attente maximale de la langue avant le premier affichage (ms) */
const LOCALE_WAIT = 1500;

/**
 * Langue du réglage chargée avant le premier affichage : la fenêtre s'ouvre
 * directement dans la bonne langue. Sans jeton, celle du système.
 */
async function initialLocale(): Promise<void> {
  if (!getToken()) {
    const system = navigator.language.slice(0, 2).toLowerCase();
    if (isSupportedLocale(system)) await setLocale(system);
    return;
  }
  const load = api
    .language()
    .then(({ language }) => setLocale(language))
    .catch(() => undefined);
  await Promise.race([load, new Promise((resolve) => setTimeout(resolve, LOCALE_WAIT))]);
}

const root = document.getElementById('root');
if (root) {
  void initialLocale().then(() =>
    createRoot(root).render(
      <StrictMode>
        {import.meta.env.VITE_REACT_PROFILE === '1' ? (
          <Profiler id="app" onRender={recordCommit}>
            <App />
          </Profiler>
        ) : (
          <App />
        )}
      </StrictMode>,
    ),
  );
}
