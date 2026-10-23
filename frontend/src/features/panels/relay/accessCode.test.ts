import { describe, expect, it } from 'vitest';

import type { RelayStatus } from '../../../lib/events';
import { accessNotice, formatAccessCode } from './accessCode';

const relay = (patch: Partial<RelayStatus>): RelayStatus => ({
  running: true,
  port: 8765,
  clients: 0,
  tunnels: {},
  url: null,
  local_url: 'http://127.0.0.1:8765/?token=t#k=k',
  access_code: '012345',
  access_failures: 0,
  access_locked: false,
  ...patch,
});

describe('code d’accès du Relay', () => {
  it('se lit en deux groupes de trois chiffres, zéros compris', () => {
    expect(formatAccessCode('012345')).toBe('012 345');
  });

  it('ne signale rien tant qu’aucun code erroné n’est saisi', () => {
    expect(accessNotice(relay({}))).toBeNull();
    // Relay d'avant le code d'accès : champs absents
    expect(
      accessNotice(relay({ access_failures: undefined, access_locked: undefined })),
    ).toBeNull();
  });

  it('signale les codes erronés, puis le verrouillage', () => {
    expect(accessNotice(relay({ access_failures: 1 }))).toEqual({
      tone: 'warning',
      text: '1 code erroné saisi. Si ce n’est pas vous, arrêtez le Relay : son lien a fuité.',
    });
    expect(accessNotice(relay({ access_failures: 3 }))?.text).toMatch(/^3 codes erronés saisis\./);
    const locked = accessNotice(relay({ access_failures: 5, access_locked: true }));
    expect(locked?.tone).toBe('error');
    expect(locked?.text).toMatch(/redémarrez-le pour un nouveau QR code et un nouveau code/);
  });
});
