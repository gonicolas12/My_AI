/*
 * Coloration du code par Shiki, dans le worker de coloration (highlight.worker.ts).
 *
 * - Moteur d'expressions régulières JavaScript : pas de WebAssembly, que la
 *   politique de sécurité de la page n'autorise pas.
 * - Thème à variables CSS : les couleurs viennent de tokens.css.
 * - Chaque langage est un morceau séparé, chargé au premier bloc qui l'utilise.
 *   La première coloration d'un langage compile sa grammaire : de 25 ms
 *   (TypeScript) à plus d'une seconde (C++). D'où le worker : la fenêtre ne
 *   l'attend jamais.
 */

import type { HighlighterCore } from 'shiki/core';

import { type CodeToken, type LanguageId, resolveLanguage } from './languages';

type LangModule = () => Promise<unknown>;

const LANGUAGES: Record<LanguageId, LangModule> = {
  bat: () => import('@shikijs/langs/bat'),
  c: () => import('@shikijs/langs/c'),
  cpp: () => import('@shikijs/langs/cpp'),
  csharp: () => import('@shikijs/langs/csharp'),
  css: () => import('@shikijs/langs/css'),
  dart: () => import('@shikijs/langs/dart'),
  diff: () => import('@shikijs/langs/diff'),
  dockerfile: () => import('@shikijs/langs/dockerfile'),
  go: () => import('@shikijs/langs/go'),
  graphql: () => import('@shikijs/langs/graphql'),
  haskell: () => import('@shikijs/langs/haskell'),
  html: () => import('@shikijs/langs/html'),
  ini: () => import('@shikijs/langs/ini'),
  java: () => import('@shikijs/langs/java'),
  javascript: () => import('@shikijs/langs/javascript'),
  json: () => import('@shikijs/langs/json'),
  jsonc: () => import('@shikijs/langs/jsonc'),
  jsx: () => import('@shikijs/langs/jsx'),
  kotlin: () => import('@shikijs/langs/kotlin'),
  latex: () => import('@shikijs/langs/latex'),
  lua: () => import('@shikijs/langs/lua'),
  makefile: () => import('@shikijs/langs/makefile'),
  markdown: () => import('@shikijs/langs/markdown'),
  matlab: () => import('@shikijs/langs/matlab'),
  nginx: () => import('@shikijs/langs/nginx'),
  perl: () => import('@shikijs/langs/perl'),
  php: () => import('@shikijs/langs/php'),
  powershell: () => import('@shikijs/langs/powershell'),
  python: () => import('@shikijs/langs/python'),
  r: () => import('@shikijs/langs/r'),
  ruby: () => import('@shikijs/langs/ruby'),
  rust: () => import('@shikijs/langs/rust'),
  scala: () => import('@shikijs/langs/scala'),
  scss: () => import('@shikijs/langs/scss'),
  shellscript: () => import('@shikijs/langs/shellscript'),
  sql: () => import('@shikijs/langs/sql'),
  swift: () => import('@shikijs/langs/swift'),
  toml: () => import('@shikijs/langs/toml'),
  tsx: () => import('@shikijs/langs/tsx'),
  typescript: () => import('@shikijs/langs/typescript'),
  xml: () => import('@shikijs/langs/xml'),
  yaml: () => import('@shikijs/langs/yaml'),
};

const THEME = 'my-ai';

let highlighter: Promise<HighlighterCore> | null = null;
/** Langage demandé → nom de sa grammaire principale chez Shiki (une fois chargée) */
const loaded = new Map<string, Promise<string>>();

type Grammar = Parameters<HighlighterCore['loadLanguage']>[0] & { name: string };

async function createHighlighter(): Promise<HighlighterCore> {
  const [{ createHighlighterCore, createCssVariablesTheme }, { createJavaScriptRegexEngine }] =
    await Promise.all([import('shiki/core'), import('shiki/engine/javascript')]);
  return createHighlighterCore({
    themes: [
      createCssVariablesTheme({
        name: THEME,
        variablePrefix: '--shiki-',
        variableDefaults: {},
        fontStyle: true,
      }),
    ],
    langs: [],
    engine: createJavaScriptRegexEngine({ forgiving: true }),
  });
}

/** Charge la grammaire d'un langage (et celles qu'elle embarque) */
function ensureLanguage(hl: HighlighterCore, id: LanguageId): Promise<string> {
  let pending = loaded.get(id);
  if (!pending) {
    pending = LANGUAGES[id]().then(async (mod) => {
      const grammars = (mod as { default: Grammar[] }).default;
      await hl.loadLanguage(...grammars);
      return grammars[grammars.length - 1]?.name ?? id;
    });
    loaded.set(id, pending);
  }
  return pending;
}

/** Jetons colorés du code, ligne par ligne ; null si le langage est inconnu */
export async function highlightCode(
  code: string,
  lang: string | undefined,
): Promise<CodeToken[][] | null> {
  const id = resolveLanguage(lang);
  if (!id) return null;
  highlighter ??= createHighlighter();
  const hl = await highlighter;
  const name = await ensureLanguage(hl, id);
  return hl
    .codeToTokensBase(code, { lang: name, theme: THEME })
    .map((line) => line.map(({ content, color, fontStyle }) => ({ content, color, fontStyle })));
}
