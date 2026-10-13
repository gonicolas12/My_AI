import { describe, expect, it } from 'vitest';

import { prepareMath } from './math';

describe('prepareMath (règle des dollars de pandoc)', () => {
  it('laisse les montants en texte', () => {
    expect(prepareMath('Entre 5 $ et 10 $.')).toEqual({
      text: 'Entre 5 \\$ et 10 \\$.',
      hasMath: false,
    });
    expect(prepareMath('De $20,000 à $30,000.').hasMath).toBe(false);
    expect(prepareMath('Prix : 3$ pièce.').hasMath).toBe(false);
  });

  it('reconnaît une formule en ligne', () => {
    expect(prepareMath('La variable $x$ vaut $x^2 + 1$.')).toEqual({
      text: 'La variable $x$ vaut $x^2 + 1$.',
      hasMath: true,
    });
  });

  it("refuse un $ fermant suivi d'un chiffre ou précédé d'une espace", () => {
    expect(prepareMath('$x$5').hasMath).toBe(false);
    expect(prepareMath('$x $ et').hasMath).toBe(false);
  });

  it('reconnaît une formule centrée $$', () => {
    const prepared = prepareMath('Avant\n\n$$\n\\frac{a}{b}\n$$\n\nAprès');
    expect(prepared.hasMath).toBe(true);
    expect(prepared.text).toContain('$$\n\\frac{a}{b}\n$$');
  });

  it('convertit \\( \\) et \\[ \\]', () => {
    expect(prepareMath('Soit \\( x^2 \\) et \\[ y = 1 \\]').text).toBe('Soit $x^2$ et $$ y = 1 $$');
  });

  it('ne touche pas au code', () => {
    const code = 'Coût : `echo $HOME` et\n```bash\nPRICE=$5\necho "$A $B"\n```\nfin 5 $';
    const prepared = prepareMath(code);
    expect(prepared.text).toContain('`echo $HOME`');
    expect(prepared.text).toContain('PRICE=$5\necho "$A $B"');
    expect(prepared.text.endsWith('fin 5 \\$')).toBe(true);
  });

  it('garde les $ déjà échappés', () => {
    expect(prepareMath('Coût : \\$5').text).toBe('Coût : \\$5');
  });
});
