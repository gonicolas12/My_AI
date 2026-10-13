import '@fontsource-variable/inter/wght.css';
import '@fontsource-variable/inter/wght-italic.css';
import '@fontsource-variable/jetbrains-mono/wght.css';
import './styles/index.css';

import { Profiler, StrictMode } from 'react';
import { createRoot } from 'react-dom/client';

import { App } from './App';
import { initToken } from './lib/api';
import { recordCommit } from './lib/profiling';

initToken();

const root = document.getElementById('root');
if (root) {
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
  );
}
