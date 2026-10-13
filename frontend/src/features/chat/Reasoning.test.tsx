import { fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';

import { Reasoning } from './Reasoning';

describe('Reasoning', () => {
  it('affiche « Réflexion » et sa durée une fois terminée, repliée', () => {
    render(
      <Reasoning
        text="🧠 Analyse :\nJe compare."
        active={false}
        durationMs={12_000}
        live={false}
      />,
    );
    const toggle = screen.getByRole('button', { name: /Réflexion/ });
    expect(toggle).toHaveTextContent('Réflexion· 12 s');
    expect(toggle).toHaveAttribute('aria-expanded', 'false');
    fireEvent.click(toggle);
    expect(toggle).toHaveAttribute('aria-expanded', 'true');
    expect(screen.getByText(/Je compare\./)).toBeInTheDocument();
  });

  it("n'a rien à déplier tant qu'aucun texte n'est arrivé", () => {
    render(<Reasoning text="" active live />);
    const toggle = screen.getByRole('button', { name: /Réflexion/ });
    expect(toggle).toBeDisabled();
    expect(toggle).not.toHaveAttribute('aria-expanded');
  });
});
