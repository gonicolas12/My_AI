import { describe, expect, it } from 'vitest';

import { BlockSplitter, lexBlocks } from './blocks';

const ANSWER = `# Titre

Un paragraphe avec du **gras**.

- un
- deux

\`\`\`python
def f():

    return 1
\`\`\`

| a | b |
|---|---|
| 1 | 2 |

$$
x^2

+ 1
$$

Fin.`;

describe('lexBlocks', () => {
  it('ne perd aucun caractère', () => {
    expect(lexBlocks(ANSWER).join('')).toBe(ANSWER);
  });

  it('garde un bloc de code entier malgré ses lignes vides', () => {
    const code = lexBlocks(ANSWER).find((block) => block.startsWith('```python'));
    expect(code).toContain('return 1');
  });

  it('ne coupe jamais une formule $$', () => {
    const math = lexBlocks(ANSWER).find((block) => block.startsWith('$$'));
    expect(math).toContain('+ 1');
    expect(math?.trimEnd().endsWith('$$')).toBe(true);
  });
});

describe('BlockSplitter', () => {
  it('donne, jeton après jeton, le même découpage que la lecture complète', () => {
    const splitter = new BlockSplitter();
    for (let end = 1; end <= ANSWER.length; end += 1) {
      const text = ANSWER.slice(0, end);
      expect(splitter.split(text)).toEqual(lexBlocks(text));
    }
    expect(splitter.split(ANSWER)).toEqual(lexBlocks(ANSWER));
  });

  it('garde les blocs déjà terminés (même objet texte)', () => {
    const splitter = new BlockSplitter();
    const first = splitter.split(ANSWER.slice(0, 60));
    const second = splitter.split(ANSWER);
    expect(second[0]).toBe(first[0]);
  });

  it('ne découpe pas un texte qui définit des liens par référence', () => {
    const text = 'Voir [la doc][1].\n\nSuite.\n\n[1]: https://example.com';
    expect(new BlockSplitter().split(text)).toEqual([text]);
  });

  it('repart de zéro pour un autre texte', () => {
    const splitter = new BlockSplitter();
    splitter.split('Premier texte.\n\nDeuxième bloc.\n\nTroisième.');
    expect(splitter.split('Autre.')).toEqual(['Autre.']);
    expect(splitter.split('')).toEqual([]);
  });
});
