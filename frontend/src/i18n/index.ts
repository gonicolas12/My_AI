/*
 * Langue de l'interface : le réglage language.default de config.yaml, qui donne
 * aussi la langue par défaut des réponses du modèle (core/i18n.py).
 *
 * Un catalogue JSON par langue (locales/) : clé à points → texte, avec ses
 * {paramètres} et, pour un nombre ({count}), ses formes du pluriel (one, few,
 * many, other…, choisies par Intl.PluralRules). Le français, langue source,
 * est chargé avec l'appli ; les autres le sont à la demande, complétés par
 * l'anglais puis le français pour une clé absente (le test des catalogues les
 * veut complets).
 *
 * t() lit la langue en cours ; dans un composant, useT() abonne en plus son
 * rendu au changement de langue, qui se fait à chaud, sans recharger la page.
 */

import { useCallback } from 'react';
import { create } from 'zustand';

import fr from './locales/fr.json';

export type MessageKey = keyof typeof fr;
export type PluralMessage = Partial<Record<Intl.LDMLPluralRule, string>> & { other: string };
export type Message = string | PluralMessage;
export type Catalog = Readonly<Record<string, Message>>;
export type Params = Readonly<Record<string, string | number>>;
export type Translate = (key: MessageKey, params?: Params) => string;

export interface LocaleInfo {
  code: string;
  /** Nom de la langue dans cette langue : lisible quelle que soit celle de l'interface */
  name: string;
  /** Étiquette BCP 47 de la page (attribut lang : choix des polices chinoises ou japonaises) */
  tag: string;
  /** Écriture de droite à gauche */
  rtl?: boolean;
}

/** Langues proposées, dans l'ordre de language.supported (config.yaml) */
export const LOCALES: readonly LocaleInfo[] = [
  { code: 'fr', name: 'Français', tag: 'fr-FR' },
  { code: 'en', name: 'English', tag: 'en-US' },
  { code: 'es', name: 'Español', tag: 'es-ES' },
  { code: 'de', name: 'Deutsch', tag: 'de-DE' },
  { code: 'it', name: 'Italiano', tag: 'it-IT' },
  { code: 'pt', name: 'Português', tag: 'pt-BR' },
  { code: 'nl', name: 'Nederlands', tag: 'nl-NL' },
  { code: 'ru', name: 'Русский', tag: 'ru-RU' },
  { code: 'zh', name: '中文', tag: 'zh-CN' },
  { code: 'ja', name: '日本語', tag: 'ja-JP' },
  { code: 'ko', name: '한국어', tag: 'ko-KR' },
  { code: 'ar', name: 'العربية', tag: 'ar', rtl: true },
];

export const DEFAULT_LOCALE = 'fr';

const SOURCE: Catalog = fr;

/** Catalogues des autres langues, chacun dans son morceau (import à la demande) */
const loaders = import.meta.glob<Catalog>(['./locales/*.json', '!./locales/fr.json'], {
  import: 'default',
});

const merged = new Map<string, Catalog>([[DEFAULT_LOCALE, SOURCE]]);

interface I18nState {
  locale: string;
  catalog: Catalog;
}

export const useI18n = create<I18nState>()(() => ({ locale: DEFAULT_LOCALE, catalog: SOURCE }));

export function localeInfo(code: string | null | undefined): LocaleInfo {
  return LOCALES.find((locale) => locale.code === code) ?? (LOCALES[0] as LocaleInfo);
}

export function isSupportedLocale(code: string | null | undefined): boolean {
  return LOCALES.some((locale) => locale.code === code);
}

/**
 * Langue des fonctions Intl (dates, heures, nombres) : celle de l'interface,
 * chiffres latins en arabe comme dans les textes traduits
 */
export function intlLocale(code: string = useI18n.getState().locale): string {
  const info = localeInfo(code);
  return info.rtl ? `${info.tag}-u-nu-latn` : info.tag;
}

const pluralRules = new Map<string, Intl.PluralRules>();

function pluralCategory(locale: string, count: number): Intl.LDMLPluralRule {
  let rules = pluralRules.get(locale);
  if (!rules) {
    rules = new Intl.PluralRules(intlLocale(locale));
    pluralRules.set(locale, rules);
  }
  return rules.select(count);
}

const PLACEHOLDER = /\{(\w+)\}/g;

function render(catalog: Catalog, locale: string, key: string, params: Params | undefined): string {
  const message = catalog[key] ?? SOURCE[key];
  if (message === undefined) return key;
  let text: string;
  if (typeof message === 'string') {
    text = message;
  } else {
    const count = Number(params?.count ?? 0);
    text = message[pluralCategory(locale, count)] ?? message.other;
  }
  if (!params) return text;
  return text.replace(PLACEHOLDER, (match, name: string) =>
    name in params ? String(params[name]) : match,
  );
}

/** Texte de la clé dans la langue en cours (hors rendu : gestionnaires, notifications) */
export function t(key: MessageKey, params?: Params): string {
  const { catalog, locale } = useI18n.getState();
  return render(catalog, locale, key, params);
}

/** t() d'un composant : son rendu suit le changement de langue */
export function useT(): Translate {
  const catalog = useI18n((state) => state.catalog);
  const locale = useI18n((state) => state.locale);
  return useCallback<Translate>(
    (key, params) => render(catalog, locale, key, params),
    [catalog, locale],
  );
}

export function useLocale(): string {
  return useI18n((state) => state.locale);
}

export function isRtl(code: string = useI18n.getState().locale): boolean {
  return Boolean(localeInfo(code).rtl);
}

/** Touches nommées dans les raccourcis (« Ctrl+Enter » → « Ctrl+Entrée », « Strg+Eingabe ») */
const KEY_NAMES: Readonly<Record<string, MessageKey>> = {
  Ctrl: 'keys.ctrl',
  Shift: 'keys.shift',
  Alt: 'keys.alt',
  Enter: 'keys.enter',
  Escape: 'keys.escape',
};

/** Raccourci affiché dans la langue de l'interface ; le code les écrit en anglais */
export function shortcutLabel(combo: string, translate: Translate = t): string {
  return combo
    .split('+')
    .map((part) => {
      const key = KEY_NAMES[part];
      return key ? translate(key) : part;
    })
    .join('+');
}

async function loadCatalog(code: string): Promise<Catalog> {
  const known = merged.get(code);
  if (known) return known;
  const load = loaders[`./locales/${code}.json`];
  if (!load) return SOURCE;
  const own = await load();
  // Clé absente : l'anglais, compris de plus de monde que le français
  const english = code === 'en' ? {} : await loadCatalog('en');
  const catalog: Catalog = { ...SOURCE, ...english, ...own };
  merged.set(code, catalog);
  return catalog;
}

function applyDocument(info: LocaleInfo): void {
  if (typeof document === 'undefined') return;
  document.documentElement.lang = info.tag;
  document.documentElement.dir = info.rtl ? 'rtl' : 'ltr';
}

let request = 0;

/** Change la langue de l'interface (à chaud) ; une langue inconnue donne le français */
export async function setLocale(code: string | null | undefined): Promise<void> {
  const info = localeInfo(code);
  const mine = ++request;
  const catalog = await loadCatalog(info.code);
  // Une demande plus récente l'emporte (choix rapides dans la liste)
  if (mine !== request) return;
  applyDocument(info);
  useI18n.setState({ locale: info.code, catalog });
}
