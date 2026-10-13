/// <reference types="vitest/config" />
import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig, type Plugin } from 'vite';

// Serveur local de l'appli en mode développement (launch_unified.py --dev) :
// même port par défaut des deux côtés, pour lancer Vite et l'appli dans
// n'importe quel ordre (cf. interfaces/desktop/lifecycle.py, DEV_BACKEND_PORT)
const backendPort = process.env.MY_AI_DESKTOP_PORT ?? '5180';
const backend = `http://127.0.0.1:${backendPort}`;

// Build de profilage (mesures du React Profiler) : VITE_REACT_PROFILE=1
const profiling = process.env.VITE_REACT_PROFILE === '1';

/**
 * KaTeX déclare chaque police en WOFF2, WOFF et TTF : la fenêtre (Chromium)
 * ne lit que le WOFF2, les deux autres alourdiraient dist/ pour rien.
 */
function katexWoff2Only(): Plugin {
  const fallbacks = /,url\([^)]+\.woff\) format\("woff"\),url\([^)]+\.ttf\) format\("truetype"\)/g;
  return {
    name: 'katex-woff2-only',
    enforce: 'pre',
    transform(code, id) {
      // Vite note les chemins avec des « / », sous Windows aussi
      if (!/\/katex\/.*\.css$/.test(id)) return null;
      return code.replace(fallbacks, '');
    },
  };
}

export default defineConfig({
  plugins: [katexWoff2Only(), react(), tailwindcss()],
  resolve: {
    alias: profiling ? [{ find: /^react-dom\/client$/, replacement: 'react-dom/profiling' }] : [],
  },
  // Worker de coloration du code : modules ES, pour charger chaque langage à part
  worker: { format: 'es' },
  server: {
    host: '127.0.0.1',
    port: 5173,
    strictPort: true,
    proxy: {
      // changeOrigin : le serveur local n'accepte que son propre en-tête Host
      '/api': { target: backend, changeOrigin: true },
      '/ws': { target: backend, ws: true, changeOrigin: true },
    },
  },
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    sourcemap: false,
    // Coloration du code et formules : chargées à la demande, en morceaux séparés
    chunkSizeWarningLimit: 1500,
  },
  test: {
    environment: 'jsdom',
    setupFiles: ['./src/test/setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    css: false,
  },
});
