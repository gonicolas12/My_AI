/**
 * Language of the extension: My_AI's own.
 *
 * The chat view, notifications, prompts and status bar speak the language
 * chosen in My_AI, like the desktop window and the phone page: the Relay
 * gives it on connection (hello_ack) and whenever it changes (« language »
 * message), and the extension remembers it for its next start. Before the
 * first connection: VS Code's language if My_AI speaks it, English otherwise.
 *
 * Texts are written in English in the code (t('Connected')); each other
 * language has its catalog, l10n/<code>.json (English text → translation),
 * read when the language is chosen. Command titles and setting descriptions
 * (package.nls.*.json) follow VS Code's language: VS Code reads them before
 * the extension runs.
 */

import * as fs from 'fs';
import * as path from 'path';
import * as vscode from 'vscode';

/** Languages of My_AI (core/i18n.py); English is the source of every text. */
export const LANGUAGES = [
  'fr', 'en', 'es', 'de', 'it', 'pt', 'nl', 'ru', 'zh', 'ja', 'ko', 'ar',
] as const;
export type Language = (typeof LANGUAGES)[number];

const STORAGE_KEY = 'myaiRelay.language.v1';

/** BCP 47 tags for times in the chat; Latin digits in Arabic, like My_AI. */
const TAGS: Record<Language, string> = {
  fr: 'fr-FR', en: 'en-US', es: 'es-ES', de: 'de-DE', it: 'it-IT', pt: 'pt-BR',
  nl: 'nl-NL', ru: 'ru-RU', zh: 'zh-CN', ja: 'ja-JP', ko: 'ko-KR', ar: 'ar-u-nu-latn',
};

let l10nDir = '';
let memento: vscode.Memento | null = null;
let current: Language = 'en';
let catalog: Record<string, string> = {};
const changed = new vscode.EventEmitter<Language>();

/** Fired when My_AI's language changes (texts already in the new language). */
export const onDidChangeLanguage = changed.event;

/** « fr-FR », « zh-cn », « pt_BR » → a language of My_AI, or null. */
export function normalizeLanguage(code: unknown): Language | null {
  if (typeof code !== 'string') {
    return null;
  }
  const base = code.trim().toLowerCase().replace(/_/g, '-').split('-')[0];
  return (LANGUAGES as readonly string[]).includes(base) ? (base as Language) : null;
}

export function initI18n(context: vscode.ExtensionContext): void {
  l10nDir = path.join(context.extensionPath, 'l10n');
  memento = context.globalState;
  const saved = normalizeLanguage(memento.get<string>(STORAGE_KEY));
  apply(saved ?? normalizeLanguage(vscode.env.language) ?? 'en');
}

/** My_AI's language, given by the Relay; returns true when it changed. */
export function setLanguage(code: unknown): boolean {
  const language = normalizeLanguage(code);
  if (!language) {
    return false;
  }
  void memento?.update(STORAGE_KEY, language);
  if (language === current) {
    return false;
  }
  apply(language);
  changed.fire(language);
  return true;
}

function apply(language: Language): void {
  current = language;
  catalog = language === 'en' ? {} : load(language);
}

function load(language: Language): Record<string, string> {
  try {
    const data: unknown = JSON.parse(
      fs.readFileSync(path.join(l10nDir, `${language}.json`), 'utf-8'),
    );
    return data && typeof data === 'object' ? (data as Record<string, string>) : {};
  } catch {
    // Missing or broken catalog: English texts
    return {};
  }
}

export function currentLanguage(): Language {
  return current;
}

/** Arabic is written right to left. */
export function isRtl(): boolean {
  return current === 'ar';
}

export function localeTag(): string {
  return TAGS[current];
}

/** Text in My_AI's language; {0}, {1}… are replaced by `args`, like vscode.l10n.t. */
export function t(source: string, ...args: Array<string | number | boolean>): string {
  const text = catalog[source] ?? source;
  if (args.length === 0) {
    return text;
  }
  return text.replace(/\{(\d+)\}/g, (match, index: string) => {
    const position = Number(index);
    return position < args.length ? String(args[position]) : match;
  });
}
