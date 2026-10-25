import { afterEach, describe, expect, it } from 'vitest';

import {
  LOCALES,
  intlLocale,
  isRtl,
  isSupportedLocale,
  localeInfo,
  setLocale,
  shortcutLabel,
  t,
  useI18n,
  type Message,
} from '.';
import fr from './locales/fr.json';

const catalogs = import.meta.glob<Record<string, Message>>('./locales/*.json', {
  eager: true,
  import: 'default',
});

function catalogOf(code: string): Record<string, Message> {
  const catalog = catalogs[`./locales/${code}.json`];
  if (!catalog) throw new Error(`catalogue ${code} absent`);
  return catalog;
}

const SOURCE: Record<string, Message> = fr;
const CODES = LOCALES.map((locale) => locale.code);
const PLACEHOLDER = /\{(\w+)\}/g;
const TAG = /<\/?(\w+)>/g;

function variants(message: Message): string[] {
  return typeof message === 'string' ? [message] : Object.values(message);
}

/** Paramètres ou balises d'un message, toutes formes du pluriel réunies */
function names(message: Message, pattern: RegExp): string[] {
  const found = variants(message).flatMap((text) =>
    [...text.matchAll(pattern)].map((match) => match[1] ?? ''),
  );
  return [...new Set(found)].sort();
}

afterEach(async () => {
  await setLocale('fr');
});

describe('catalogues', () => {
  it('un catalogue par langue proposée, et rien d’autre', () => {
    const files = Object.keys(catalogs)
      .map((path) => path.replace('./locales/', '').replace('.json', ''))
      .sort();
    expect(files).toEqual([...CODES].sort());
  });

  it.each(CODES)('%s : les clés du français, ni plus ni moins', (code) => {
    expect(Object.keys(catalogOf(code))).toEqual(Object.keys(SOURCE));
  });

  it.each(CODES)('%s : mêmes paramètres et balises que le français, aucun texte vide', (code) => {
    const catalog = catalogOf(code);
    for (const [key, source] of Object.entries(SOURCE)) {
      const message = catalog[key] as Message;
      expect(names(message, PLACEHOLDER), key).toEqual(names(source, PLACEHOLDER));
      expect(names(message, TAG), key).toEqual(names(source, TAG));
      for (const text of variants(message)) expect(text.trim(), key).not.toBe('');
    }
  });

  it.each(CODES)('%s : une forme du pluriel pour chaque nombre entier', (code) => {
    const rules = new Intl.PluralRules(intlLocale(code));
    const catalog = catalogOf(code);
    for (const [key, source] of Object.entries(SOURCE)) {
      if (typeof source === 'string') continue;
      const message = catalog[key];
      expect(typeof message, key).toBe('object');
      // 0 à 1000 : toutes les formes des nombres entiers (zero, two, few, many…)
      for (let count = 0; count <= 1000; count += 1) {
        const category = rules.select(count);
        expect(message, `${key} (${count} → ${category})`).toHaveProperty(category);
      }
    }
  });
});

describe('t et setLocale', () => {
  it('rend le français par défaut, paramètres et pluriels compris', () => {
    expect(useI18n.getState().locale).toBe('fr');
    expect(t('sidebar.search.count', { count: 0 })).toBe('0 résultat');
    expect(t('sidebar.search.count', { count: 1 })).toBe('1 résultat');
    expect(t('sidebar.search.count', { count: 2 })).toBe('2 résultats');
    expect(t('connection.httpError', { status: 404 })).toBe('Erreur 404');
  });

  it('change de langue à chaud', async () => {
    await setLocale('en');
    expect(t('composer.send')).toBe('Send');
    expect(t('sidebar.search.count', { count: 1 })).toBe('1 result');
    expect(t('sidebar.search.count', { count: 0 })).toBe('0 results');
    expect(document.documentElement.lang).toBe('en-US');
    expect(document.documentElement.dir).toBe('ltr');
  });

  it('suit les formes du russe (1, 3, 5, 21)', async () => {
    await setLocale('ru');
    expect(t('sidebar.search.count', { count: 1 })).toBe('1 результат');
    expect(t('sidebar.search.count', { count: 3 })).toBe('3 результата');
    expect(t('sidebar.search.count', { count: 5 })).toBe('5 результатов');
    expect(t('sidebar.search.count', { count: 21 })).toBe('21 результат');
  });

  it('écrit l’arabe de droite à gauche, chiffres latins', async () => {
    await setLocale('ar');
    expect(document.documentElement.dir).toBe('rtl');
    expect(document.documentElement.lang).toBe('ar');
    expect(isRtl()).toBe(true);
    expect(intlLocale()).toBe('ar-u-nu-latn');
    expect(new Intl.NumberFormat(intlLocale()).format(12)).toBe('12');
    expect(t('sidebar.search.count', { count: 2 })).toBe('نتيجتان');
    await setLocale('fr');
    expect(document.documentElement.dir).toBe('ltr');
  });

  it('nomme les touches des raccourcis dans la langue', async () => {
    expect(shortcutLabel('Ctrl+Shift+Enter')).toBe('Ctrl+Maj+Entrée');
    await setLocale('de');
    expect(shortcutLabel('Ctrl+Shift+Enter')).toBe('Strg+Umschalt+Eingabe');
    expect(shortcutLabel('Ctrl+K')).toBe('Strg+K');
  });

  it('prend le français pour une langue inconnue', async () => {
    await setLocale('en');
    await setLocale('xx');
    expect(useI18n.getState().locale).toBe('fr');
    expect(isSupportedLocale('xx')).toBe(false);
    expect(localeInfo('xx').code).toBe('fr');
  });

  it('retient la dernière langue demandée', async () => {
    const first = setLocale('es');
    const last = setLocale('it');
    await Promise.all([first, last]);
    expect(useI18n.getState().locale).toBe('it');
    expect(t('composer.send')).toBe('Invia');
  });

  it('nomme chaque langue dans sa propre langue', () => {
    expect(localeInfo('ja').name).toBe('日本語');
    expect(localeInfo('ar').name).toBe('العربية');
    expect(new Set(LOCALES.map((locale) => locale.name)).size).toBe(LOCALES.length);
  });
});
