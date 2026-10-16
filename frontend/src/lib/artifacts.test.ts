import { describe, expect, it } from 'vitest';

import {
  detectArtifacts,
  documentArtifacts,
  formatLabel,
  isPreviewable,
  messageArtifacts,
} from './artifacts';

describe('détection des artefacts (miroir de interfaces/artifacts.py)', () => {
  it('trouve les blocs HTML et SVG, avec leur titre', () => {
    const text = [
      'Voici la page :',
      '```html',
      '<!doctype html><html><head><title>Ma page</title></head><body>Salut</body></html>',
      '```',
      'Et le logo :',
      '```svg',
      '<svg width="10" height="10"><circle r="4"/></svg>',
      '```',
    ].join('\n');
    const found = detectArtifacts(text);
    expect(found.map((a) => [a.kind, a.title, a.index])).toEqual([
      ['html', 'Ma page', 0],
      ['svg', 'SVG #2', 1],
    ]);
  });

  it('prend le premier <h1> à défaut de <title>', () => {
    const [artifact] = detectArtifacts(
      '```html\n<div><h1>Tableau <em>de bord</em></h1></div>\n```',
    );
    expect(artifact?.title).toBe('Tableau de bord');
  });

  it('ignore le code qui ne se rend pas, et le XML sans HTML', () => {
    expect(detectArtifacts('```xml\n<config><a/></config>\n```\n```js\nx\n```')).toEqual([]);
    expect(detectArtifacts('```json\n{"a": 1}\n```')).toEqual([]);
  });

  it('suit Python quand du code contient une balise HTML', () => {
    // _classify : hors langage HTML déclaré, la balise suffit (même règle des deux côtés)
    const [artifact] = detectArtifacts('```python\nprint("<div>")\n```');
    expect([artifact?.kind, artifact?.language]).toEqual(['html', 'python']);
  });

  it('numérote les blocs parmi tous les blocs de code', () => {
    const text = '```js\nlet a\n```\n```html\n<div>x</div>\n```';
    expect(detectArtifacts(text)[0]?.index).toBe(1);
  });
});

describe('documents', () => {
  it('garde les formats qui ont un aperçu, sans doublon', () => {
    const docs = documentArtifacts(
      ['C:\\out\\rapport.docx', 'c:/out/rapport.docx', 'C:\\out\\script.py', 'C:\\out\\note.pdf'],
      2,
    );
    expect(docs.map((d) => [d.title, d.index, d.generated])).toEqual([
      ['rapport.docx', 2, true],
      ['note.pdf', 3, true],
    ]);
  });

  it('place les documents après les blocs de code', () => {
    const items = messageArtifacts('```html\n<div>x</div>\n```', ['/tmp/a.xlsx']);
    expect(items.map((item) => item.kind)).toEqual(['html', 'document']);
  });

  it('nomme les formats', () => {
    expect(formatLabel('C:/a/b.docx')).toBe('Document Word');
    expect(formatLabel('calcul.py')).toBe('Fichier py');
    expect(isPreviewable('notes.MD')).toBe(true);
    expect(isPreviewable('archive.zip')).toBe(false);
  });
});
