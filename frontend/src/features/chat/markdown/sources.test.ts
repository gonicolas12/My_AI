import { describe, expect, it } from 'vitest';

import { splitSources } from './sources';

const ANSWER = 'La population atteint 8,3 milliards [1], en hausse de 0,8 % [3].';

describe('bloc des sources en fin de réponse', () => {
  it('le retire du texte affiché et en garde les sources, numéros compris', () => {
    const text = [
      ANSWER,
      '',
      '📚 **Sources**',
      '[1] [Population mondiale — Wikipédia](https://fr.wikipedia.org/wiki/Population_mondiale)',
      '[3] https://www.worldometers.info/fr/',
    ].join('\n');
    expect(splitSources(text)).toEqual({
      body: ANSWER,
      sources: [
        {
          n: 1,
          title: 'Population mondiale — Wikipédia',
          url: 'https://fr.wikipedia.org/wiki/Population_mondiale',
          host: 'fr.wikipedia.org',
        },
        // Sans titre : le nom du site
        {
          n: 3,
          title: 'www.worldometers.info',
          url: 'https://www.worldometers.info/fr/',
          host: 'www.worldometers.info',
        },
      ],
    });
  });

  it("le cache dès son en-tête pendant l'écriture, sans la ligne inachevée", () => {
    const head = `${ANSWER}\n\n📚 **Sources**`;
    expect(splitSources(head)).toEqual({ body: ANSWER, sources: [] });
    const partial = `${head}\n[1] [Population mondiale](https://fr.wiki`;
    expect(splitSources(partial)).toEqual({ body: ANSWER, sources: [] });
  });

  it("laisse le texte entier quand l'en-tête n'ouvre pas le bloc final", () => {
    expect(splitSources(ANSWER)).toEqual({ body: ANSWER, sources: [] });
    const prose = `📚 **Sources**\nLes chiffres viennent de l'ONU.\n\n${ANSWER}`;
    expect(splitSources(prose)).toEqual({ body: prose, sources: [] });
  });

  it("accepte l'en-tête sans gras", () => {
    const text = `${ANSWER}\n\n📚 Sources\n[1] [ONU](https://www.un.org/fr/)`;
    expect(splitSources(text).sources.map((source) => source.host)).toEqual(['www.un.org']);
  });
});
