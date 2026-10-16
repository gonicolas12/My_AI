/* Durée d'un fil en cours, rafraîchie chaque seconde */

import { useEffect, useState } from 'react';

/** Secondes écoulées depuis `since`, rafraîchies chaque seconde tant que `active` */
export function useElapsed(since: string, active: boolean): number {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    if (!active) return undefined;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [active]);
  const start = Date.parse(since);
  return Number.isNaN(start) ? 0 : Math.max(0, Math.floor((now - start) / 1000));
}

/** « 0:48 », « 12:05 » */
export function clock(seconds: number): string {
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${String(seconds % 60).padStart(2, '0')}`;
}
