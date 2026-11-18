import { act, render, screen, waitFor } from '@testing-library/react';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import type { PreviewView } from '../../lib/api';
import { NativeDocument } from './NativeDocument';
import {
  claimNative,
  coversNative,
  deviceRect,
  nativeAppLabel,
  resetNativeClaims,
} from './nativeLayer';

const native = vi.hoisted(() => ({
  available: vi.fn(() => Promise.resolve(true)),
  show: vi.fn(() => Promise.resolve(true)),
  place: vi.fn(),
  close: vi.fn(),
}));
vi.mock('../../lib/shell', () => ({ shell: { nativePreview: native } }));

const VIEW: PreviewView = {
  id: 'apercu-1',
  kind: 'native',
  title: 'rapport.docx',
  url: '',
  path: 'C:/docs/rapport.docx',
};

const box = (left: number, top: number, width: number, height: number) =>
  new DOMRect(left, top, width, height);

/** Place du document : à droite, sous l'en-tête du volet */
const SLOT = box(900, 48, 540, 852);

function stubRect(element: Element, rect: DOMRect) {
  Object.defineProperty(element, 'getBoundingClientRect', {
    configurable: true,
    value: () => rect,
  });
}

beforeAll(() => {
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  };
});

beforeEach(() => {
  vi.clearAllMocks();
  resetNativeClaims();
  document.body.innerHTML = '';
});

describe('nativeLayer', () => {
  it('convertit en pixels de l’écran, échelle comprise', () => {
    expect(deviceRect(box(900.4, 48, 540, 852), 1.25)).toEqual({
      x: 1126,
      y: 60,
      width: 675,
      height: 1065,
    });
    expect(deviceRect(box(0, 0, 0, 0), 1)).toEqual({ x: 0, y: 0, width: 1, height: 1 });
  });

  it('nomme l’application de la visionneuse', () => {
    expect(nativeAppLabel('C:/a/Rapport.DOCX')).toBe('Word');
    expect(nativeAppLabel('plan.pptx')).toBe('PowerPoint');
    expect(nativeAppLabel('budget.xlsm')).toBe('Excel');
    expect(nativeAppLabel('note.md')).toBe('');
  });

  it('se masque sous un dialogue, ou une couche qui touche sa place', () => {
    expect(coversNative(SLOT)).toBe(false);

    const dialog = document.createElement('div');
    dialog.setAttribute('role', 'dialog');
    document.body.append(dialog);
    expect(coversNative(SLOT)).toBe(true);
    dialog.remove();

    const region = document.createElement('div');
    region.setAttribute('data-toast-region', '');
    const toast = document.createElement('div');
    region.append(toast);
    document.body.append(region);
    stubRect(toast, box(1104, 64, 320, 44));
    expect(coversNative(SLOT)).toBe(true);
    // Infobulle de la barre latérale, loin du volet
    stubRect(toast, box(20, 64, 320, 44));
    expect(coversNative(SLOT)).toBe(false);
  });

  it('ne se masque pas sous son propre dialogue, ni sous ceux qu’il recouvre', () => {
    const below = document.createElement('div');
    below.setAttribute('role', 'dialog');
    const own = document.createElement('div');
    own.setAttribute('role', 'dialog');
    const slot = document.createElement('div');
    own.append(slot);
    document.body.append(below, own);
    // Fenêtre d'aperçu (own) ouverte au-dessus d'un panneau (below)
    expect(coversNative(SLOT, document, slot)).toBe(false);
    // Confirmation ouverte par-dessus la fenêtre d'aperçu : masquée
    const confirm = document.createElement('div');
    confirm.setAttribute('role', 'alertdialog');
    document.body.append(confirm);
    expect(coversNative(SLOT, document, slot)).toBe(true);
    // Hors de tout dialogue (volet du chat) : tout dialogue la masque
    expect(coversNative(SLOT, document, document.createElement('div'))).toBe(true);
  });

  it('une seule visionneuse : le dernier aperçu la prend, le précédent la retrouve', () => {
    const first = { resume: vi.fn(), suspend: vi.fn() };
    const second = { resume: vi.fn(), suspend: vi.fn() };
    const a = claimNative(first);
    expect(a.owns()).toBe(true);
    const b = claimNative(second);
    expect(first.suspend).toHaveBeenCalledTimes(1);
    expect([a.owns(), b.owns()]).toEqual([false, true]);
    b.release();
    expect(first.resume).toHaveBeenCalledTimes(1);
    expect(native.close).not.toHaveBeenCalled();
    a.release();
    // Plus aucun aperçu : la visionneuse se ferme
    expect(native.close).toHaveBeenCalledTimes(1);
    a.release();
    expect(native.close).toHaveBeenCalledTimes(1);
  });
});

describe('NativeDocument', () => {
  it('charge masquée, se pose une fois prête, se masque sous un dialogue', async () => {
    const { container, unmount } = render(
      <NativeDocument view={VIEW} hidden={false} onFailed={vi.fn()} />,
    );
    expect(screen.getByText('Ouverture de l’aperçu Word…')).toBeInTheDocument();
    expect(native.show).toHaveBeenCalledWith('apercu-1', { x: 0, y: 0, width: 1, height: 1 });

    await waitFor(() => expect(native.place).toHaveBeenCalledWith(expect.anything(), true));
    expect(container.querySelector('[data-native-preview="ready"]')).not.toBeNull();

    const dialog = document.createElement('div');
    dialog.setAttribute('role', 'dialog');
    act(() => document.body.append(dialog));
    await waitFor(() => expect(native.place).toHaveBeenLastCalledWith(expect.anything(), false));
    act(() => dialog.remove());
    await waitFor(() => expect(native.place).toHaveBeenLastCalledWith(expect.anything(), true));

    unmount();
    expect(native.close).toHaveBeenCalledTimes(1);
  });

  it('reste masquée pendant le redimensionnement du volet', async () => {
    const { rerender } = render(<NativeDocument view={VIEW} hidden={false} onFailed={vi.fn()} />);
    await waitFor(() => expect(native.place).toHaveBeenLastCalledWith(expect.anything(), true));
    rerender(<NativeDocument view={VIEW} hidden onFailed={vi.fn()} />);
    await waitFor(() => expect(native.place).toHaveBeenLastCalledWith(expect.anything(), false));
  });

  it('un aperçu Office ouvert par-dessus prend la visionneuse, le premier la retrouve ensuite', async () => {
    const other: PreviewView = { ...VIEW, id: 'apercu-2', path: 'C:/docs/budget.xlsx' };
    const first = render(<NativeDocument view={VIEW} hidden={false} onFailed={vi.fn()} />);
    await waitFor(() => expect(native.place).toHaveBeenCalled());
    const second = render(<NativeDocument view={other} hidden={false} onFailed={vi.fn()} />);
    await waitFor(() =>
      expect(native.show).toHaveBeenLastCalledWith('apercu-2', expect.anything()),
    );
    // Cédée sans être fermée : le second document s'y charge
    expect(native.close).not.toHaveBeenCalled();
    second.unmount();
    await waitFor(() =>
      expect(native.show).toHaveBeenLastCalledWith('apercu-1', expect.anything()),
    );
    expect(native.close).not.toHaveBeenCalled();
    first.unmount();
    expect(native.close).toHaveBeenCalledTimes(1);
  });

  it('visionneuse en échec : repli sur l’aperçu HTML', async () => {
    native.show.mockResolvedValueOnce(false);
    const onFailed = vi.fn();
    render(<NativeDocument view={VIEW} hidden={false} onFailed={onFailed} />);
    await waitFor(() => expect(onFailed).toHaveBeenCalledTimes(1));
    expect(native.place).not.toHaveBeenCalled();
  });
});
