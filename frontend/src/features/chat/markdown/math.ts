/*
 * Formules LaTeX : préparation du texte pour remark-math (D9).
 *
 * - \( … \) devient $…$ et \[ … \] devient $$…$$ (délimiteurs fréquents chez qwen).
 * - Un $ n'ouvre une formule que s'il est suivi d'un caractère autre qu'une
 *   espace, et ne la ferme que s'il suit un tel caractère et n'est pas suivi
 *   d'un chiffre (règle de pandoc). Les autres $ sont échappés : « entre 5 $
 *   et 10 $ » ou « $20,000 et $30,000 » restent des montants.
 * - Le code (blocs et `code` en ligne) n'est jamais modifié.
 */

export interface PreparedMath {
  text: string;
  hasMath: boolean;
}

const FENCE = /^ {0,3}(`{3,}|~{3,})/;

/** Découpe en segments de code (laissés tels quels) et de texte */
function segments(text: string): { code: boolean; value: string }[] {
  const out: { code: boolean; value: string }[] = [];
  const lines = text.split(/(?<=\n)/);
  let fence: string | null = null;
  let buffer = '';
  let bufferIsCode = false;
  const flush = () => {
    if (buffer) out.push({ code: bufferIsCode, value: buffer });
    buffer = '';
  };
  for (const line of lines) {
    const match = FENCE.exec(line);
    if (fence === null && match?.[1]) {
      flush();
      fence = match[1];
      bufferIsCode = true;
      buffer = line;
      continue;
    }
    if (fence !== null) {
      buffer += line;
      const closing = FENCE.exec(line);
      if (
        closing?.[1] &&
        closing[1][0] === fence[0] &&
        closing[1].length >= fence.length &&
        line.trim() === closing[1]
      ) {
        flush();
        fence = null;
        bufferIsCode = false;
      }
      continue;
    }
    buffer += line;
  }
  flush();
  // Code en ligne dans les segments de texte
  const result: { code: boolean; value: string }[] = [];
  for (const seg of out) {
    if (seg.code) {
      result.push(seg);
      continue;
    }
    let rest = seg.value;
    for (;;) {
      const open = /`+/.exec(rest);
      if (!open) break;
      const ticks = open[0];
      const closeAt = rest.indexOf(ticks, open.index + ticks.length);
      if (closeAt < 0) break;
      const end = closeAt + ticks.length;
      if (open.index > 0) result.push({ code: false, value: rest.slice(0, open.index) });
      result.push({ code: true, value: rest.slice(open.index, end) });
      rest = rest.slice(end);
    }
    if (rest) result.push({ code: false, value: rest });
  }
  return result;
}

const isSpace = (ch: string | undefined) => ch === undefined || /\s/.test(ch);
const isDigit = (ch: string | undefined) => ch !== undefined && ch >= '0' && ch <= '9';

/** \( … \) → $…$ et \[ … \] → $$…$$, si le délimiteur fermant existe */
function convertLatexDelimiters(text: string): string {
  let out = text.replace(/\\\[([\s\S]+?)\\\]/g, (_m, body: string) => `$$${body}$$`);
  out = out.replace(/\\\(([^\n]+?)\\\)/g, (_m, body: string) => `$${body.trim()}$`);
  return out;
}

function escapeLoneDollars(text: string): { text: string; hasMath: boolean } {
  let out = '';
  let hasMath = false;
  let i = 0;
  while (i < text.length) {
    const ch = text[i];
    if (ch === '\\' && i + 1 < text.length) {
      out += text.slice(i, i + 2);
      i += 2;
      continue;
    }
    if (ch !== '$') {
      out += ch;
      i += 1;
      continue;
    }
    // $$ … $$ : formule centrée, jusqu'au $$ suivant
    if (text[i + 1] === '$') {
      const close = text.indexOf('$$', i + 2);
      if (close > i + 2) {
        out += text.slice(i, close + 2);
        hasMath = true;
        i = close + 2;
      } else {
        out += '\\$\\$';
        i += 2;
      }
      continue;
    }
    // $ … $ : formule en ligne, dans le même paragraphe
    let closeAt = -1;
    if (!isSpace(text[i + 1])) {
      for (let j = i + 1; j < text.length; j += 1) {
        const c = text[j];
        if (c === '\\') {
          j += 1;
          continue;
        }
        if (c === '\n' && text[j + 1] === '\n') break;
        if (c === '$') {
          if (text[j + 1] === '$') break;
          if (!isSpace(text[j - 1]) && !isDigit(text[j + 1])) closeAt = j;
          break;
        }
      }
    }
    if (closeAt > i + 1) {
      out += text.slice(i, closeAt + 1);
      hasMath = true;
      i = closeAt + 1;
    } else {
      out += '\\$';
      i += 1;
    }
  }
  return { text: out, hasMath };
}

/** Prépare un bloc Markdown pour le rendu des formules */
export function prepareMath(text: string): PreparedMath {
  if (!text.includes('$') && !text.includes('\\(') && !text.includes('\\[')) {
    return { text, hasMath: false };
  }
  let hasMath = false;
  const parts = segments(text).map((seg) => {
    if (seg.code) return seg.value;
    const prepared = escapeLoneDollars(convertLatexDelimiters(seg.value));
    hasMath ||= prepared.hasMath;
    return prepared.text;
  });
  return { text: parts.join(''), hasMath };
}
