import { act, fireEvent, render, screen } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import { Tooltip, TooltipProvider } from './Tooltip';

beforeEach(() => {
  globalThis.ResizeObserver ??= class {
    observe() {}
    unobserve() {}
    disconnect() {}
  } as unknown as typeof ResizeObserver;
});

function renderButton() {
  render(
    <TooltipProvider delayDuration={0} disableHoverableContent>
      <Tooltip label="Mémoire">
        <button type="button">M</button>
      </Tooltip>
    </TooltipProvider>,
  );
  return screen.getByRole('button', { name: 'M' });
}

describe('infobulles (essai de la phase 5 : elles restaient affichées)', () => {
  it('ne s’ouvrent pas sur un focus rendu sans clavier, comme au retour dans la fenêtre', () => {
    const button = renderButton();
    fireEvent.pointerDown(document.body); // dernière action : la souris
    act(() => button.focus());
    expect(screen.queryByRole('tooltip')).toBeNull();
  });

  it('s’ouvrent au focus quand on navigue au clavier (Tab)', () => {
    const button = renderButton();
    fireEvent.keyDown(window, { key: 'Tab' });
    act(() => button.focus());
    expect(screen.getByRole('tooltip')).toHaveTextContent('Mémoire');
  });

  it('se ferment quand la fenêtre perd le focus', () => {
    const button = renderButton();
    fireEvent.keyDown(window, { key: 'Tab' });
    act(() => button.focus());
    expect(screen.getByRole('tooltip')).toBeInTheDocument();
    act(() => {
      window.dispatchEvent(new Event('blur'));
    });
    expect(screen.queryByRole('tooltip')).toBeNull();
  });
});
