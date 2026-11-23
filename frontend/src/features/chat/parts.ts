/*
 * Une réponse peut enchaîner un préambule, des appels d'outils, puis la
 * synthèse : le texte est coupé aux positions des appels (champ « at »,
 * longueur du texte au moment de l'appel, en caractères : textIndex) pour les
 * afficher à leur place. Sans position (session ancienne), les outils viennent
 * en tête.
 */

import type { ToolCallView } from '../../lib/events';

export type Part =
  { kind: 'text'; key: string; text: string } | { kind: 'tool'; key: string; tool: ToolCallView };

/**
 * Indice dans text (unités UTF-16 de JavaScript) d'une position « at » du serveur,
 * comptée en caractères (len() de Python). Un emoji hors du plan de base (« 😊 »)
 * compte pour un là-bas, pour deux ici : sans conversion, la carte d'un outil appelé
 * à la fin d'une réponse pleine d'emojis tombait avant sa fin, et le dernier emoji
 * s'affichait après elle.
 */
export function textIndex(text: string, at: number): number {
  let index = 0;
  for (let count = 0; count < at && index < text.length; count += 1) {
    index += (text.codePointAt(index) ?? 0) > 0xffff ? 2 : 1;
  }
  return Math.min(index, text.length);
}

export function buildParts(text: string, tools: ToolCallView[]): Part[] {
  const ordered = tools
    .map((tool, index) => ({
      tool,
      index,
      at: textIndex(text, tool.at ?? 0),
    }))
    .sort((a, b) => a.at - b.at || a.index - b.index);
  const parts: Part[] = [];
  let cursor = 0;
  const pushText = (end: number) => {
    const chunk = text.slice(cursor, end);
    if (chunk.trim()) parts.push({ kind: 'text', key: `t${cursor}`, text: chunk });
    cursor = end;
  };
  for (const { tool, index, at } of ordered) {
    if (at > cursor) pushText(at);
    // « synthesis » annonce seulement la rédaction de la réponse
    if (tool.name !== 'synthesis') parts.push({ kind: 'tool', key: `x${index}`, tool });
  }
  if (cursor < text.length) pushText(text.length);
  return parts;
}
