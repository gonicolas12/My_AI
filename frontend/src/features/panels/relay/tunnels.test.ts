import { describe, expect, it } from 'vitest';

import type { RelayStatus } from '../../../lib/events';
import { tunnelView } from './tunnels';

const ROUTER = 'https://gonicolas12.github.io/My_AI/router.html#d=abc';

const relay = (patch: Partial<RelayStatus>): RelayStatus => ({
  running: true,
  port: 8765,
  clients: 0,
  tunnels: {},
  tunnel_states: {},
  url: null,
  local_url: 'http://127.0.0.1:8765/?token=t#k=k',
  ...patch,
});

describe('tunnels du Relay', () => {
  it('attend les tunnels, puis leur vérification', () => {
    expect(tunnelView(relay({}))).toMatchObject({
      ready: false,
      busy: true,
      status: 'Tunnels en cours de connexion…',
      others: [],
    });
    // localhost.run annoncé : pas de QR code tant que le PC ne l'a pas joint
    const announced = tunnelView(
      relay({
        tunnels: { 'localhost.run': 'https://a.lhr.life' },
        tunnel_states: { 'localhost.run': 'checking' },
      }),
    );
    expect(announced).toMatchObject({
      ready: false,
      busy: true,
      status: 'Vérification des tunnels…',
    });
    expect(announced.others).toEqual([{ name: 'localhost.run', label: 'vérification…' }]);
  });

  it('ne compte comme actifs que les tunnels joignables, et nomme les muets', () => {
    const view = tunnelView(
      relay({
        tunnels: {
          'localhost.run': 'https://a.lhr.life',
          cloudflared: 'https://b.trycloudflare.com',
        },
        tunnel_states: { 'localhost.run': 'dead', cloudflared: 'ok' },
        url: ROUTER,
      }),
    );
    expect(view).toMatchObject({
      ready: true,
      busy: false,
      tone: 'success',
      status: 'Tunnels actifs : cloudflared',
    });
    expect(view.others).toEqual([{ name: 'localhost.run', label: 'ne répond pas' }]);
  });

  it('signale un QR code repris sans vérification (aucun tunnel joint depuis ce PC)', () => {
    const view = tunnelView(
      relay({
        tunnels: { 'localhost.run': 'https://a.lhr.life' },
        tunnel_states: { 'localhost.run': 'dead' },
        url: ROUTER,
      }),
    );
    expect(view).toMatchObject({ ready: true, busy: false, tone: 'warning' });
    expect(view.status).toContain('Aucun tunnel ne répond depuis ce PC');
  });

  it('tient un tunnel sans état pour « en vérification »', () => {
    const view = tunnelView(
      relay({ tunnels: { serveo: 'https://c.serveo.net' }, tunnel_states: undefined }),
    );
    expect(view.others).toEqual([{ name: 'serveo', label: 'vérification…' }]);
  });
});
