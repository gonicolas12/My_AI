/*
 * État des tunnels du Relay, tel que le panneau l'affiche. Le Relay vérifie
 * chaque tunnel annoncé depuis ce PC (la requête de la page de routage) : seuls
 * les joignables entrent dans le QR code. Si aucun ne répond au PC au bout de
 * 30 s, le QR code les reprend tous (le téléphone peut les joindre quand le PC
 * ne le peut pas), et le panneau le signale.
 */

import { type MessageKey, t as translate, type Translate } from '../../../i18n';
import type { RelayStatus, TunnelState } from '../../../lib/events';

export interface TunnelView {
  /** La page de routage existe : QR code, et son lien à copier (téléphone, extension VS Code) */
  ready: boolean;
  /** Ligne d'état et sa couleur ; `busy` : tunnels pas encore prêts */
  status: string;
  tone: 'success' | 'warning';
  busy: boolean;
  /** Tunnels annoncés hors du QR code, avec leur état */
  others: { name: string; label: string }[];
}

const LABEL: Record<Exclude<TunnelState, 'ok'>, MessageKey> = {
  checking: 'relay.tunnel.checking',
  dead: 'relay.tunnel.dead',
};

export function tunnelView(relay: RelayStatus, t: Translate = translate): TunnelView {
  const names = Object.keys(relay.tunnels).sort();
  const states = relay.tunnel_states ?? {};
  const state = (name: string): TunnelState => states[name] ?? 'checking';
  const reachable = names.filter((name) => state(name) === 'ok');
  const others = names
    .filter((name) => state(name) !== 'ok')
    .map((name) => ({ name, label: t(LABEL[state(name) as Exclude<TunnelState, 'ok'>]) }));
  const ready = Boolean(relay.url) && names.length > 0;

  if (ready && reachable.length) {
    return {
      ready,
      status: t('relay.tunnels.active', { list: reachable.join(', ') }),
      tone: 'success',
      busy: false,
      others,
    };
  }
  if (ready) {
    return {
      ready,
      status: t('relay.tunnels.noneFromPc'),
      tone: 'warning',
      busy: false,
      others,
    };
  }
  return {
    ready,
    status: names.length ? t('relay.tunnels.checking') : t('relay.tunnels.connecting'),
    tone: 'warning',
    busy: true,
    others,
  };
}
