/** Heure « 14:05 » d'un horodatage ISO ('' s'il est invalide) */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' });
}

/** Durée lisible : « 850 ms », « 12 s », « 1 min 05 s » */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms) || ms < 0) return '';
  if (ms < 1000) return `${Math.round(ms)} ms`;
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return `${seconds} s`;
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return `${minutes} min ${String(rest).padStart(2, '0')} s`;
}

/** Nombre à virgule française : 72,4 */
export function formatDecimal(value: number, digits = 1): string {
  return value.toLocaleString('fr-FR', {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

/** Date relative pour la liste des conversations : « Aujourd'hui », « Hier », « 12 oct. » */
export function formatDay(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const startOf = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((startOf(now) - startOf(date)) / 86_400_000);
  if (days === 0) return "Aujourd'hui";
  if (days === 1) return 'Hier';
  if (days > 1 && days < 7) return date.toLocaleDateString('fr-FR', { weekday: 'long' });
  return date.toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'short',
    ...(date.getFullYear() === now.getFullYear() ? {} : { year: 'numeric' }),
  });
}
