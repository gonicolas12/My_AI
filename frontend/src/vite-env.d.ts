/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Build de profilage (React Profiler), pour les mesures de performance */
  readonly VITE_REACT_PROFILE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
