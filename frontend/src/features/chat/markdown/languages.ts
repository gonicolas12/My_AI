/*
 * Langages colorés et leurs alias (« py » → « python »). Sans import : partagé
 * par la fenêtre et le worker de coloration.
 */

export const LANGUAGE_IDS = [
  'bat',
  'c',
  'cpp',
  'csharp',
  'css',
  'dart',
  'diff',
  'dockerfile',
  'go',
  'graphql',
  'haskell',
  'html',
  'ini',
  'java',
  'javascript',
  'json',
  'jsonc',
  'jsx',
  'kotlin',
  'latex',
  'lua',
  'makefile',
  'markdown',
  'matlab',
  'nginx',
  'perl',
  'php',
  'powershell',
  'python',
  'r',
  'ruby',
  'rust',
  'scala',
  'scss',
  'shellscript',
  'sql',
  'swift',
  'toml',
  'tsx',
  'typescript',
  'xml',
  'yaml',
] as const;

export type LanguageId = (typeof LANGUAGE_IDS)[number];

const KNOWN = new Set<string>(LANGUAGE_IDS);

const ALIASES: Record<string, LanguageId> = {
  'c#': 'csharp',
  'c++': 'cpp',
  bash: 'shellscript',
  batch: 'bat',
  cmd: 'bat',
  cs: 'csharp',
  docker: 'dockerfile',
  golang: 'go',
  htm: 'html',
  js: 'javascript',
  kt: 'kotlin',
  make: 'makefile',
  md: 'markdown',
  node: 'javascript',
  ps: 'powershell',
  ps1: 'powershell',
  py: 'python',
  python3: 'python',
  rb: 'ruby',
  rs: 'rust',
  sh: 'shellscript',
  shell: 'shellscript',
  svg: 'xml',
  tex: 'latex',
  ts: 'typescript',
  yml: 'yaml',
  zsh: 'shellscript',
};

/** Identifiant du langage d'un bloc de code, ou null (texte brut) */
export function resolveLanguage(lang: string | undefined): LanguageId | null {
  const key = (lang ?? '').trim().toLowerCase();
  if (!key) return null;
  const id = ALIASES[key] ?? key;
  return KNOWN.has(id) ? (id as LanguageId) : null;
}

/** Jeton coloré, tel que le worker le renvoie */
export interface CodeToken {
  content: string;
  color?: string | undefined;
  fontStyle?: number | undefined;
}
