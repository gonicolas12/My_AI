import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { AnyServerEvent } from './events';
import { formatDay, formatDecimal, formatDuration, formatTime } from './format';
import { cssColorToHex, externalUrl } from './shell';
import { comboOf, isBrowserShortcut } from './shortcuts';
import { EventSocket, ReplyError, SocketError } from './ws';

function key(init: KeyboardEventInit): KeyboardEvent {
  return new KeyboardEvent('keydown', init);
}

describe('raccourcis', () => {
  it('neutralise ceux du navigateur', () => {
    expect(isBrowserShortcut(key({ key: 'F5' }))).toBe(true);
    expect(isBrowserShortcut(key({ key: 'r', ctrlKey: true }))).toBe(true);
    expect(isBrowserShortcut(key({ key: 'R', ctrlKey: true, shiftKey: true }))).toBe(true);
    expect(isBrowserShortcut(key({ key: 'p', ctrlKey: true }))).toBe(true);
    expect(isBrowserShortcut(key({ key: 'ArrowLeft', altKey: true }))).toBe(true);
  });

  it("laisse ceux de l'édition de texte", () => {
    for (const letter of ['c', 'v', 'x', 'a', 'z', 'y']) {
      expect(isBrowserShortcut(key({ key: letter, ctrlKey: true }))).toBe(false);
    }
    expect(isBrowserShortcut(key({ key: 'Enter' }))).toBe(false);
  });

  it('normalise les combinaisons', () => {
    expect(comboOf(key({ key: 'n', ctrlKey: true }))).toBe('Ctrl+N');
    expect(comboOf(key({ key: 'Escape' }))).toBe('Escape');
    expect(comboOf(key({ key: ',', ctrlKey: true }))).toBe('Ctrl+,');
  });
});

describe('liens et couleurs', () => {
  it('ne laisse sortir que les liens web', () => {
    expect(externalUrl('https://example.com')).toBe('https://example.com/');
    expect(externalUrl('mailto:a@b.fr')).toBe('mailto:a@b.fr');
    expect(externalUrl('javascript:alert(1)')).toBeNull();
    expect(externalUrl('file:///C:/a.exe')).toBeNull();
    expect(externalUrl('/api/status')).toBeNull(); // page de l'appli
  });

  it('convertit une couleur calculée en #rrggbb', () => {
    expect(cssColorToHex('rgb(15, 15, 15)')).toBe('#0f0f0f');
    expect(cssColorToHex('rgba(255, 107, 71, 1)')).toBe('#ff6b47');
    expect(cssColorToHex('#FF6B47')).toBe('#ff6b47');
    expect(cssColorToHex('transparent')).toBeNull();
  });
});

describe('formats', () => {
  it('écrit les durées', () => {
    expect(formatDuration(850)).toBe('850 ms');
    expect(formatDuration(12_400)).toBe('12 s');
    expect(formatDuration(65_000)).toBe('1 min 05 s');
    expect(formatDuration(undefined)).toBe('');
  });

  it("écrit l'heure, les nombres et les jours en français", () => {
    expect(formatTime('2026-10-12T14:05:00')).toBe('14:05');
    expect(formatTime('pas une date')).toBe('');
    expect(formatDecimal(72.44)).toBe('72,4');
    const now = new Date('2026-10-12T15:00:00');
    expect(formatDay('2026-10-12T09:00:00', now)).toBe("Aujourd'hui");
    expect(formatDay('2026-10-11T09:00:00', now)).toBe('Hier');
  });
});

// ── WebSocket ─────────────────────────────────────────────────────────────

class FakeWebSocket {
  static readonly OPEN = 1;
  static instances: FakeWebSocket[] = [];
  readyState = 0;
  sent: string[] = [];
  onmessage: ((message: MessageEvent<string>) => void) | null = null;
  onclose: (() => void) | null = null;
  readonly url: string;

  constructor(url: string) {
    this.url = url;
    FakeWebSocket.instances.push(this);
  }

  send(data: string) {
    this.sent.push(data);
  }

  close() {
    this.readyState = 3;
    this.onclose?.();
  }

  open() {
    this.readyState = FakeWebSocket.OPEN;
  }

  receive(data: unknown) {
    this.onmessage?.({ data: JSON.stringify(data) } as MessageEvent<string>);
  }
}

function serverEvent(seq: number): AnyServerEvent {
  return {
    type: 'notification',
    conversation_id: null,
    message_id: null,
    seq,
    payload: { level: 'info', message: String(seq) },
  };
}

describe('EventSocket', () => {
  beforeEach(() => {
    FakeWebSocket.instances = [];
    vi.stubGlobal('WebSocket', FakeWebSocket);
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.unstubAllGlobals();
  });

  it("relit l'état à la première connexion, puis reprend sans doublon", () => {
    const events: number[] = [];
    const hellos: boolean[] = [];
    const socket = new EventSocket(() => 'ws://127.0.0.1:1/ws?token=t', {
      onEvent: (event) => events.push(event.seq),
      onHello: (resync) => hellos.push(resync),
      onState: () => undefined,
    });
    socket.start();
    const first = FakeWebSocket.instances[0]!;
    first.open();
    first.receive({ type: 'hello', resumed: true });
    first.receive(serverEvent(1));
    first.receive(serverEvent(2));
    first.close();

    vi.advanceTimersByTime(300);
    const second = FakeWebSocket.instances[1]!;
    expect(second.url).toContain('since=2');
    second.open();
    second.receive({ type: 'hello', resumed: true });
    second.receive(serverEvent(2)); // rejoué deux fois : ignoré
    second.receive(serverEvent(3));
    expect(events).toEqual([1, 2, 3]);
    expect(hellos).toEqual([true, false]);
    socket.stop();
  });

  it('relit tout si le serveur ne peut pas rejouer', () => {
    const hellos: boolean[] = [];
    const socket = new EventSocket(() => 'ws://x/ws', {
      onEvent: () => undefined,
      onHello: (resync) => hellos.push(resync),
      onState: () => undefined,
    });
    socket.start();
    FakeWebSocket.instances[0]!.receive({ type: 'hello', resumed: true });
    FakeWebSocket.instances[0]!.close();
    vi.advanceTimersByTime(300);
    FakeWebSocket.instances[1]!.receive({ type: 'hello', resumed: false });
    expect(hellos).toEqual([true, true]);
    socket.stop();
  });

  it('rend la réponse du serveur, ou son refus', async () => {
    const socket = new EventSocket(() => 'ws://x/ws', {
      onEvent: () => undefined,
      onHello: () => undefined,
      onState: () => undefined,
    });
    await expect(socket.send({ type: 'chat.stop' })).rejects.toMatchObject({ sent: false });
    socket.start();
    const ws = FakeWebSocket.instances[0]!;
    ws.open();
    const ok = socket.send({ type: 'chat.stop' });
    const sent = JSON.parse(ws.sent[0]!) as { id: string };
    ws.receive({ type: 'reply', ref: sent.id, ok: true, data: { stopped: true } });
    await expect(ok).resolves.toEqual({ stopped: true });

    const refused = socket.send({ type: 'chat.send', text: '' });
    const second = JSON.parse(ws.sent[1]!) as { id: string };
    ws.receive({ type: 'reply', ref: second.id, ok: false, error: 'Message vide.' });
    await expect(refused).rejects.toBeInstanceOf(ReplyError);

    const lost = socket.send({ type: 'chat.stop' });
    ws.close();
    await expect(lost).rejects.toBeInstanceOf(SocketError);
    await expect(lost).rejects.toMatchObject({ sent: true });
    socket.stop();
  });
});
