import { intlLocale, t } from '../i18n';

/**
 * Emoji de tête d'un message du serveur (« ✅ … », format de l'interface Tk) :
 * dans une notification, l'icône du niveau le remplace
 */
const LEADING_EMOJI = /^(?:\p{Extended_Pictographic}|\p{Variation_Selector}|\u{200D}|\s)+/u;

export function withoutLeadingEmoji(message: string): string {
  return message.replace(LEADING_EMOJI, '') || message;
}

/** Heure « 14:05 » d'un horodatage ISO ('' s'il est invalide) */
export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleTimeString(intlLocale(), { hour: '2-digit', minute: '2-digit' });
}

/** Durée lisible : « 850 ms », « 12 s », « 1 min 05 s » (unités de la langue) */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms) || ms < 0) return '';
  if (ms < 1000) return t('format.ms', { n: Math.round(ms) });
  const seconds = Math.round(ms / 1000);
  if (seconds < 60) return t('format.seconds', { n: seconds });
  const minutes = Math.floor(seconds / 60);
  const rest = seconds % 60;
  return t('format.minutesSeconds', { m: minutes, s: String(rest).padStart(2, '0') });
}

/** Nombre décimal dans la langue de l'interface : 72,4 en français, 72.4 en anglais */
export function formatDecimal(value: number, digits = 1): string {
  return value.toLocaleString(intlLocale(), {
    minimumFractionDigits: 0,
    maximumFractionDigits: digits,
  });
}

const SIZE_UNITS = ['byte', 'kilobyte', 'megabyte', 'gigabyte'] as const;

/** Taille d'un fichier dans la langue de l'interface : « 38,4 ko », « 38.4 kB » */
export function formatSize(bytes: number | null | undefined): string {
  if (bytes === null || bytes === undefined || !Number.isFinite(bytes) || bytes < 0) return '';
  let value = bytes;
  let unit = 0;
  while (value >= 1000 && unit < SIZE_UNITS.length - 1) {
    value /= 1000;
    unit += 1;
  }
  return new Intl.NumberFormat(intlLocale(), {
    style: 'unit',
    unit: SIZE_UNITS[unit],
    unitDisplay: 'short',
    maximumFractionDigits: unit === 0 || value >= 100 ? 0 : 1,
  }).format(value);
}

/** Unités de la date relative et leur taille dans l'unité suivante (secondes d'abord) */
const RELATIVE_STEPS: [Intl.RelativeTimeFormatUnit, number][] = [
  ['minute', 60],
  ['hour', 24],
  ['day', 7],
];

/**
 * Date d'un fichier, relative si elle est proche : « il y a 7 heures », « hier »,
 * puis « 30 oct. » (comme l'en-tête d'un aperçu de document)
 */
export function formatWhen(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const relative = new Intl.RelativeTimeFormat(intlLocale(), { numeric: 'auto' });
  const seconds = (date.getTime() - now.getTime()) / 1000;
  if (Math.abs(seconds) < 45) return relative.format(0, 'second');
  // En minutes, puis en heures, puis en jours
  let value = seconds / 60;
  for (const [unit, size] of RELATIVE_STEPS) {
    const rounded = Math.round(value);
    if (Math.abs(rounded) < size) return relative.format(rounded || Math.sign(value), unit);
    value /= size;
  }
  return date.toLocaleDateString(intlLocale(), {
    day: 'numeric',
    month: 'short',
    ...(date.getFullYear() === now.getFullYear() ? {} : { year: 'numeric' }),
  });
}

/** Date relative pour la liste des conversations : « Aujourd'hui », « Hier », « 12 oct. » */
export function formatDay(iso: string | null | undefined, now: Date = new Date()): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const startOf = (d: Date) => new Date(d.getFullYear(), d.getMonth(), d.getDate()).getTime();
  const days = Math.round((startOf(now) - startOf(date)) / 86_400_000);
  if (days === 0) return t('format.today');
  if (days === 1) return t('format.yesterday');
  if (days > 1 && days < 7) return date.toLocaleDateString(intlLocale(), { weekday: 'long' });
  return date.toLocaleDateString(intlLocale(), {
    day: 'numeric',
    month: 'short',
    ...(date.getFullYear() === now.getFullYear() ? {} : { year: 'numeric' }),
  });
}
