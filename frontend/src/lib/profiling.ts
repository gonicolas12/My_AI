/*
 * Mesures du React Profiler (build de profilage seulement : VITE_REACT_PROFILE=1,
 * cf. vite.config.ts). Chaque rendu validé est gardé dans window.__myAiCommits,
 * que lisent les scripts de mesure (Playwright).
 */

import type { ProfilerOnRenderCallback } from 'react';

export interface CommitRecord {
  phase: string;
  actualDuration: number;
  commitTime: number;
}

declare global {
  interface Window {
    __myAiCommits?: CommitRecord[];
  }
}

export const recordCommit: ProfilerOnRenderCallback = (
  _id,
  phase,
  actualDuration,
  _base,
  _start,
  commitTime,
) => {
  const commits = (window.__myAiCommits ??= []);
  commits.push({ phase, actualDuration, commitTime });
};
