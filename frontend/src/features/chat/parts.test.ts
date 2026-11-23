import { describe, expect, it } from 'vitest';

import { splitAttachmentLines } from './attachments';
import { buildParts, textIndex } from './parts';
import { toolOutcome, toolText } from './tools';

describe('buildParts', () => {
  it('place chaque outil à sa position dans le texte', () => {
    const parts = buildParts('Je cherche.\n\nVoici la réponse.', [
      { name: 'web_search', label: 'Recherche', at: 11, ok: true, sources: 3 },
      { name: 'synthesis', label: 'Synthèse', at: 13 },
    ]);
    expect(parts.map((part) => (part.kind === 'text' ? part.text : `[${part.tool.name}]`))).toEqual(
      ['Je cherche.', '[web_search]', 'Voici la réponse.'],
    );
  });

  it('met en tête les outils sans position (session ancienne)', () => {
    const parts = buildParts('Réponse', [{ name: 'calculate', label: 'Calcul' }]);
    expect(parts.map((part) => part.kind)).toEqual(['tool', 'text']);
  });

  it('garde des clés stables pendant le streaming', () => {
    const tools = [{ name: 'web_search', label: 'R', at: 5 }];
    const before = buildParts('Avant\n\nDébut', tools);
    const after = buildParts('Avant\n\nDébut de la suite', tools);
    expect(after.map((part) => part.key)).toEqual(before.map((part) => part.key));
  });

  it('compte les emojis comme le serveur (un caractère chacun)', () => {
    // Le serveur donne la longueur de Python : 3 caractères ici, 5 unités en JavaScript.
    // La carte « Mémorisé », envoyée après la réponse, tombait avant son dernier emoji
    const text = 'Bon appétit 🥗 ! 😊';
    const at = [...text].length;
    const parts = buildParts(text, [{ name: 'remember_fact', label: 'Mémorisé', at }]);
    expect(parts.map((part) => (part.kind === 'text' ? part.text : `[${part.tool.name}]`))).toEqual(
      ['Bon appétit 🥗 ! 😊', '[remember_fact]'],
    );
    // Au milieu : coupé au bon endroit, même après un emoji
    const middle = buildParts('🥗 Salade.\n\nSuite', [
      { name: 'web_search', label: 'R', at: [...'🥗 Salade.'].length },
    ]);
    expect(middle.map((part) => (part.kind === 'text' ? part.text : `[${part.tool.name}]`))).toEqual(
      ['🥗 Salade.', '[web_search]', '\n\nSuite'],
    );
  });
});

describe('textIndex', () => {
  it('passe d’une position en caractères à un indice JavaScript', () => {
    expect(textIndex('abc', 2)).toBe(2);
    expect(textIndex('a😊b', 2)).toBe(3);
    expect(textIndex('😊😊', 2)).toBe(4);
    expect(textIndex('é🌱', 1)).toBe(1);
    expect(textIndex('a😊', 0)).toBe(0);
    // Au-delà du texte (réponse plus courte, sources retirées) : sa fin
    expect(textIndex('a😊', 9)).toBe(3);
  });
});

describe('outils', () => {
  it("retire l'emoji de tête du libellé", () => {
    expect(toolText('🔍 Recherche sur internet : « café »')).toBe(
      'Recherche sur internet : « café »',
    );
    expect(toolText('Calcul')).toBe('Calcul');
  });

  it('résume une recherche web par son nombre de sources', () => {
    expect(toolOutcome({ name: 'web_search', label: '', ok: true, sources: 1 })).toBe('1 source');
    expect(toolOutcome({ name: 'web_search', label: '', ok: true, sources: 3 })).toBe('3 sources');
    expect(toolOutcome({ name: 'web_search', label: '' })).toBeNull();
  });
});

describe('splitAttachmentLines', () => {
  it('sépare les lignes de pièces jointes du texte (format Tk)', () => {
    expect(splitAttachmentLines('Résume ce fichier\n📎 rapport.pdf\n🖼️ photo.png')).toEqual({
      body: 'Résume ce fichier',
      lines: ['📎 rapport.pdf', '🖼️ photo.png'],
    });
    expect(splitAttachmentLines('Pas de pièce jointe')).toEqual({
      body: 'Pas de pièce jointe',
      lines: [],
    });
  });
});
