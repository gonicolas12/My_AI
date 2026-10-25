/*
 * Code d'accès du Relay, affiché sous le QR code : le téléphone et l'extension
 * VS Code le demandent en plus du lien, qui peut fuiter sans que l'écran soit vu
 * (historique synchronisé, presse-papiers). Le Relay compte les codes erronés :
 * seul qui a le lien peut en essayer un, et passé 5 il n'en accepte plus aucun
 * avant son redémarrage.
 */

import { t as translate, type Translate } from '../../../i18n';
import type { RelayStatus } from '../../../lib/events';

/** « 012345 » → « 012 345 », plus facile à lire puis à taper */
export function formatAccessCode(code: string): string {
  return code.length === 6 ? `${code.slice(0, 3)} ${code.slice(3)}` : code;
}

export interface AccessNotice {
  tone: 'warning' | 'error';
  text: string;
}

/** Codes erronés : signalés (le lien a peut-être fuité), puis le verrouillage */
export function accessNotice(relay: RelayStatus, t: Translate = translate): AccessNotice | null {
  if (relay.access_locked) {
    return { tone: 'error', text: t('relay.access.locked') };
  }
  const failures = relay.access_failures ?? 0;
  if (!failures) return null;
  return {
    tone: 'warning',
    text: t('relay.access.warning', {
      failures: t('relay.access.failures', { count: failures }),
    }),
  };
}
