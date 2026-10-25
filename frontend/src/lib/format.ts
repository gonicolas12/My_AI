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
