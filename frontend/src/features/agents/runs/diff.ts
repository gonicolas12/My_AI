/*
 * Diff d'un code modifié par un agent (§8 : « quand un agent modifie du code
 * fourni, sa sortie se relit sous forme de diff »).
 *
 * Code fourni : fichier de code joint à la tâche (gardé dans le fil, `sources`)
 * ou bloc de code écrit dans la tâche. Dans la sortie de l'agent, le bloc de
 * code le plus proche d'un code fourni, sans lui être identique, est montré en
 * diff par lignes (algorithme de Myers) ; la réponse entière reste dans
 * l'onglet Sortie.
 */

import { t as translate, type Translate } from '../../../i18n';

export interface CodeBlock {
  lang: string;
  code: string;
}

export type DiffKind = ' ' | '-' | '+';

export interface DiffLine {
  kind: DiffKind;
  /** Numéro de ligne dans l'original (lignes gardées ou retirées) */
  old?: number;
  /** Numéro de ligne dans la nouvelle version (lignes gardées ou ajoutées) */
  new?: number;
  text: string;
}

export interface CodeChange {
  /** Nom du code fourni : fichier joint, ou « code de la tâche » */
  name: string;
  block: CodeBlock;
  lines: DiffLine[];
  added: number;
  removed: number;
}

/** Au-delà, pas de diff : le calcul et l'affichage seraient trop lourds */
const MAX_DIFF_LINES = 6000;
/** Part minimale de lignes communes pour voir une modification, pas un autre code */
const MIN_OVERLAP = 0.3;

const FENCE = /^( {0,3})(`{3,}|~{3,})[ \t]*([^\s`]*)[^\n]*$/;

/** Blocs de code clos d'un texte Markdown (un bloc encore ouvert n'en est pas un) */
export function codeBlocks(markdown: string): CodeBlock[] {
  const blocks: CodeBlock[] = [];
  let open: { fence: string; lang: string; body: string[] } | null = null;
  for (const line of markdown.split('\n')) {
    if (!open) {
      const match = FENCE.exec(line);
      if (match) open = { fence: match[2] ?? '```', lang: match[3] ?? '', body: [] };
      continue;
    }
    const trimmed = line.trim();
    if (trimmed.startsWith(open.fence) && /^[`~]+$/.test(trimmed) && trimmed[0] === open.fence[0]) {
      blocks.push({ lang: open.lang.toLowerCase(), code: open.body.join('\n') });
      open = null;
      continue;
    }
    open.body.push(line);
  }
  return blocks;
}

function splitLines(code: string): string[] {
  const lines = code.replace(/\r\n/g, '\n').split('\n');
  if (lines.length > 1 && lines[lines.length - 1] === '') lines.pop();
  return lines;
}

/** Diff par lignes (Myers, O((N+M)·D)) ; null si les textes sont trop longs */
export function diffLines(a: string[], b: string[]): DiffLine[] | null {
  const n = a.length;
  const m = b.length;
  if (n + m > MAX_DIFF_LINES) return null;
  const max = n + m;
  const offset = max + 1;
  const v = new Int32Array(2 * max + 3);
  const trace: Int32Array[] = [];
  let found = false;
  for (let d = 0; d <= max && !found; d++) {
    trace.push(v.slice());
    for (let k = -d; k <= d; k += 2) {
      const down = k === -d || (k !== d && (v[k - 1 + offset] ?? 0) < (v[k + 1 + offset] ?? 0));
      let x = down ? (v[k + 1 + offset] ?? 0) : (v[k - 1 + offset] ?? 0) + 1;
      let y = x - k;
      while (x < n && y < m && a[x] === b[y]) {
        x += 1;
        y += 1;
      }
      v[k + offset] = x;
      if (x >= n && y >= m) {
        found = true;
        break;
      }
    }
  }
  // Retour en arrière, de la fin vers le début
  const out: DiffLine[] = [];
  let x = n;
  let y = m;
  for (let d = trace.length - 1; d >= 0; d--) {
    const prev = trace[d] as Int32Array;
    const k = x - y;
    const down = k === -d || (k !== d && (prev[k - 1 + offset] ?? 0) < (prev[k + 1 + offset] ?? 0));
    const prevK = down ? k + 1 : k - 1;
    const prevX = prev[prevK + offset] ?? 0;
    const prevY = prevX - prevK;
    while (x > prevX && y > prevY) {
      out.push({ kind: ' ', old: x, new: y, text: a[x - 1] ?? '' });
      x -= 1;
      y -= 1;
    }
    if (d > 0) {
      if (x === prevX) {
        out.push({ kind: '+', new: y, text: b[y - 1] ?? '' });
        y -= 1;
      } else {
        out.push({ kind: '-', old: x, text: a[x - 1] ?? '' });
        x -= 1;
      }
    }
  }
  return out.reverse();
}

/** Ligne qui porte du contenu (ni vide, ni seulement des accolades ou une ponctuation) */
function meaningful(text: string): boolean {
  return text.replace(/[\s{}()[\];,:.]/g, '').length >= 3;
}

/**
 * Part du code le plus court qui se retrouve dans l'autre (0 : rien en commun).
 * Une réécriture courte d'une longue fonction en garde la signature : elle
 * compte comme une modification.
 */
function overlap(lines: DiffLine[], before: string[], after: string[]): number {
  const common = lines.filter((line) => line.kind === ' ' && meaningful(line.text)).length;
  const shorter = Math.min(before.filter(meaningful).length, after.filter(meaningful).length);
  return shorter ? common / shorter : 0;
}

/** Codes fournis à l'agent : fichiers joints, puis blocs de code de la tâche */
export function providedCode(
  sources: { name: string; text: string }[],
  task: string,
  t: Translate = translate,
): { name: string; text: string }[] {
  const fromTask = codeBlocks(task).map((block) => ({
    name: t('agents.diff.taskCode'),
    text: block.code,
  }));
  return [...sources, ...fromTask].filter((source) => splitLines(source.text).length >= 2);
}

/** Bloc de la sortie qui modifie un code fourni, avec son diff ; null s'il n'y en a pas */
export function findCodeChange(
  output: string,
  provided: { name: string; text: string }[],
): CodeChange | null {
  if (!provided.length) return null;
  let best: (CodeChange & { score: number }) | null = null;
  for (const block of codeBlocks(output)) {
    const after = splitLines(block.code);
    if (after.length < 2) continue;
    for (const source of provided) {
      const before = splitLines(source.text);
      const lines = diffLines(before, after);
      if (!lines) continue;
      const score = overlap(lines, before, after);
      const added = lines.filter((line) => line.kind === '+').length;
      const removed = lines.filter((line) => line.kind === '-').length;
      if (score < MIN_OVERLAP || (!added && !removed)) continue;
      if (!best || score > best.score) {
        best = { name: source.name, block, lines, added, removed, score };
      }
    }
  }
  if (!best) return null;
  return {
    name: best.name,
    block: best.block,
    lines: best.lines,
    added: best.added,
    removed: best.removed,
  };
}

export type DiffRow = DiffLine | { kind: 'gap'; hidden: number };

/** Lignes à montrer : les changements et `context` lignes autour, le reste replié */
export function diffRows(lines: DiffLine[], context = 3): DiffRow[] {
  const keep = new Array<boolean>(lines.length).fill(false);
  lines.forEach((line, index) => {
    if (line.kind === ' ') return;
    for (
      let i = Math.max(0, index - context);
      i <= Math.min(lines.length - 1, index + context);
      i++
    ) {
      keep[i] = true;
    }
  });
  const rows: DiffRow[] = [];
  let hidden = 0;
  lines.forEach((line, index) => {
    if (keep[index]) {
      if (hidden) rows.push({ kind: 'gap', hidden });
      hidden = 0;
      rows.push(line);
    } else {
      hidden += 1;
    }
  });
  if (hidden) rows.push({ kind: 'gap', hidden });
  return rows;
}
