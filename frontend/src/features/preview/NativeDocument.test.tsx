import { act, render, screen, waitFor } from '@testing-library/react';
import { beforeAll, beforeEach, describe, expect, it, vi } from 'vitest';

import type { PreviewView } from '../../lib/api';
import { NativeDocument } from './NativeDocument';
import { coversNative, deviceRect, nativeAppLabel } from './nativeLayer';

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

  it('visionneuse en échec : repli sur l’aperçu HTML', async () => {
    native.show.mockResolvedValueOnce(false);
    const onFailed = vi.fn();
    render(<NativeDocument view={VIEW} hidden={false} onFailed={onFailed} />);
    await waitFor(() => expect(onFailed).toHaveBeenCalledTimes(1));
    expect(native.place).not.toHaveBeenCalled();
  });
});
