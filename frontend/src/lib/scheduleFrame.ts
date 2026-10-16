/*
 * Regroupe le travail à l'image suivante : les jetons reçus pendant une image
 * ne provoquent qu'un rendu. Une fenêtre réduite ne reçoit plus d'images
 * (requestAnimationFrame suspendu) : un minuteur prend alors le relais, pour
 * que l'état reste à jour.
 */

const FALLBACK_DELAY = 120;

export function createFrameBatcher<T>(flush: (items: T[]) => void): {
  push: (item: T) => void;
  flushNow: () => void;
} {
  let items: T[] = [];
  let frame: number | null = null;
  let timer: ReturnType<typeof setTimeout> | null = null;

  const run = () => {
    if (frame !== null) cancelAnimationFrame(frame);
    if (timer !== null) clearTimeout(timer);
    frame = null;
    timer = null;
    if (!items.length) return;
    const batch = items;
    items = [];
    flush(batch);
  };

  return {
    push(item: T) {
      items.push(item);
      if (frame === null) frame = requestAnimationFrame(run);
      if (timer === null) timer = setTimeout(run, FALLBACK_DELAY);
    },
    flushNow: run,
  };
}
