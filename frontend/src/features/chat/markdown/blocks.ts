/*
 * Découpage d'une réponse Markdown en blocs (paragraphe, liste, tableau, bloc
 * de code…), pour ne re-rendre pendant le streaming que le dernier : les
 * blocs terminés gardent leur rendu.
 *
 * Même principe que Streamdown : jetons de bloc de marked, lignes vides
 * rattachées au bloc précédent, formule $$…$$ jamais coupée.
 */

import { Lexer } from 'marked';

/** Note de bas de page ou lien par référence : ils lient des blocs éloignés */
const CROSS_BLOCK_DEFINITION = /^ {0,3}\[[^\]\n]+\]:\s*\S/m;

function displayMathCount(text: string): number {
  let count = 0;
  for (let i = 0; i < text.length - 1; i += 1) {
    if (text[i] === '$' && text[i + 1] === '$') {
      count += 1;
      i += 1;
    }
  }
  return count;
}

export function lexBlocks(text: string): string[] {
  const tokens = new Lexer({ gfm: true }).blockTokens(text);
  const blocks: string[] = [];
  const append = (chunk: string, merge: boolean) => {
    const last = blocks.length - 1;
    const previous = blocks[last];
    if (previous !== undefined && (merge || displayMathCount(previous) % 2 === 1)) {
      blocks[last] = previous + chunk;
    } else {
      blocks.push(chunk);
    }
  };
  let offset = 0;
  for (const token of tokens) {
    // marked réécrit parfois la fin d'un texte incomplet (« + » seul…) : les
    // blocs ne sont coupés qu'aux jetons qui recopient fidèlement le texte
    if (!text.startsWith(token.raw, offset)) break;
    append(token.raw, token.type === 'space');
    offset += token.raw.length;
  }
  if (offset < text.length) {
    const rest = text.slice(offset);
    append(rest, !rest.trim());
  }
  return blocks;
}

/**
 * Découpe incrémental : le texte d'une réponse en cours ne fait que
 * s'allonger, seuls ses deux derniers blocs sont relus.
 */
export class BlockSplitter {
  private input = '';
  private blocks: string[] = [];

  split(text: string): string[] {
    if (text === this.input) return this.blocks;
    if (!text) {
      this.input = '';
      this.blocks = [];
      return this.blocks;
    }
    if (CROSS_BLOCK_DEFINITION.test(text)) {
      this.input = text;
      this.blocks = [text];
      return this.blocks;
    }
    let keep = 0;
    let offset = 0;
    if (this.blocks.length > 2 && text.startsWith(this.input)) {
      keep = this.blocks.length - 2;
      for (let i = 0; i < keep; i += 1) offset += this.blocks[i]?.length ?? 0;
    }
    const tail = lexBlocks(text.slice(offset));
    this.blocks = keep ? [...this.blocks.slice(0, keep), ...tail] : tail;
    this.input = text;
    return this.blocks;
  }
}
