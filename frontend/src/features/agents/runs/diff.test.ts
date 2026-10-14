import { describe, expect, it } from 'vitest';

import { codeBlocks, diffLines, diffRows, findCodeChange, providedCode } from './diff';

describe('codeBlocks', () => {
  it('lit les blocs clos, avec leur langage, et laisse le bloc ouvert', () => {
    const text = 'Avant\n```Python\na = 1\nb = 2\n```\nMilieu\n~~~js\nx()\n~~~\n```py\nencore';
    const blocks = codeBlocks(text);
    expect(blocks.map((block) => [block.lang, block.code])).toEqual([
      ['python', 'a = 1\nb = 2'],
      ['js', 'x()'],
    ]);
  });
});

describe('diffLines', () => {
  it('retrouve les lignes gardées, retirées et ajoutées, avec leurs numéros', () => {
    const lines = diffLines(['a', 'b', 'c', 'd'], ['a', 'x', 'c', 'd', 'e']);
    expect(lines).toEqual([
      { kind: ' ', old: 1, new: 1, text: 'a' },
      { kind: '-', old: 2, text: 'b' },
      { kind: '+', new: 2, text: 'x' },
      { kind: ' ', old: 3, new: 3, text: 'c' },
      { kind: ' ', old: 4, new: 4, text: 'd' },
      { kind: '+', new: 5, text: 'e' },
    ]);
  });

  it('gère les textes vides et identiques', () => {
    expect(diffLines([], [])).toEqual([]);
    expect(diffLines([], ['a'])).toEqual([{ kind: '+', new: 1, text: 'a' }]);
    expect(diffLines(['a'], [])).toEqual([{ kind: '-', old: 1, text: 'a' }]);
    expect(diffLines(['a', 'b'], ['a', 'b'])?.every((line) => line.kind === ' ')).toBe(true);
  });

  it('recompose les deux versions sur un cas plus long', () => {
    const before = Array.from({ length: 60 }, (_, i) => `ligne ${i % 7} ${i % 3}`);
    const after = before
      .filter((_, i) => i % 5 !== 0)
      .map((line, i) => (i % 9 ? line : `${line}!`));
    const lines = diffLines(before, after) ?? [];
    expect(lines.filter((l) => l.kind !== '+').map((l) => l.text)).toEqual(before);
    expect(lines.filter((l) => l.kind !== '-').map((l) => l.text)).toEqual(after);
  });

  it('renonce au-delà de la limite', () => {
    const big = Array.from({ length: 4000 }, (_, i) => String(i));
    expect(diffLines(big, big)).toBeNull();
  });
});

describe('findCodeChange', () => {
  const source =
    'def chercher(livres, mot):\n    resultats = []\n    for l in livres:\n        if mot in l:\n            resultats.append(l)\n    return resultats\n';

  it('trouve le bloc qui modifie le fichier joint', () => {
    const output =
      'Voici la version optimisée :\n\n```python\ndef chercher(livres, mot):\n    return [l for l in livres if mot in l]\n```\n\nPlus court.';
    const change = findCodeChange(output, providedCode([{ name: 'utils.py', text: source }], ''));
    expect(change?.name).toBe('utils.py');
    expect(change?.added).toBe(1);
    expect(change?.removed).toBe(5);
  });

  it('prend aussi un bloc de code écrit dans la tâche', () => {
    const task = `Corrige ce code :\n\`\`\`python\n${source}\`\`\``;
    const output =
      '```python\n' + source.replace('return resultats', 'return sorted(resultats)') + '```';
    const change = findCodeChange(output, providedCode([], task));
    expect(change?.name).toBe('code de la tâche');
    expect(change?.added).toBe(1);
    expect(change?.removed).toBe(1);
  });

  it('ne montre ni un code identique, ni un autre code, ni rien sans code fourni', () => {
    const same = '```python\n' + source + '```';
    expect(findCodeChange(same, providedCode([{ name: 'u.py', text: source }], ''))).toBeNull();
    const other = '```js\nconst a = 1;\nconsole.log(a);\nexport default a;\n```';
    expect(findCodeChange(other, providedCode([{ name: 'u.py', text: source }], ''))).toBeNull();
    expect(findCodeChange(same, [])).toBeNull();
  });
});

describe('diffRows', () => {
  it('replie les lignes identiques loin des changements', () => {
    const before = Array.from({ length: 20 }, (_, i) => `l${i}`);
    const after = before.map((line, i) => (i === 10 ? 'changée' : line));
    const rows = diffRows(diffLines(before, after) ?? [], 2);
    expect(rows[0]).toEqual({ kind: 'gap', hidden: 8 });
    expect(rows.filter((row) => row.kind !== 'gap')).toHaveLength(6);
    expect(rows[rows.length - 1]).toEqual({ kind: 'gap', hidden: 7 });
  });
});
