import { afterEach, describe, expect, it, vi } from 'vitest';

import { platform, revealLabels } from './platform';

const MAC =
  'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko)';
const LINUX =
  'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15';

afterEach(() => {
  vi.restoreAllMocks();
});

describe('système de la machine', () => {
  it('se lit dans l’agent de la page : WebView2, WKWebView, WebKitGTK', () => {
    expect(platform(navigator.userAgent)).toBe('windows');
    expect(platform(MAC)).toBe('mac');
    expect(platform(LINUX)).toBe('linux');
    // Inconnu : Windows, celui de la plupart
    expect(platform('')).toBe('windows');
  });

  it('donne le libellé du gestionnaire de fichiers de ce système', () => {
    expect(revealLabels()).toEqual({ file: 'chat.file.reveal', path: 'chat.path.reveal' });
    vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue(MAC);
    expect(revealLabels()).toEqual({ file: 'chat.file.revealMac', path: 'chat.path.revealMac' });
    vi.spyOn(navigator, 'userAgent', 'get').mockReturnValue(LINUX);
    expect(revealLabels()).toEqual({
      file: 'chat.file.revealLinux',
      path: 'chat.path.revealLinux',
    });
  });
});
