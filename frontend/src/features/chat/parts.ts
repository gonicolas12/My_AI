/*
 * Une réponse peut enchaîner un préambule, des appels d'outils, puis la
 * synthèse : le texte est coupé aux positions des appels (champ « at »,
 * longueur du texte au moment de l'appel) pour les afficher à leur place.
 * Sans position (session ancienne), les outils viennent en tête.
 */

import type { ToolCallView } from '../../lib/events';

export type Part =
  { kind: 'text'; key: string; text: string } | { kind: 'tool'; key: string; tool: ToolCallView };

export function buildParts(text: string, tools: ToolCallView[]): Part[] {
  const ordered = tools
    .map((tool, index) => ({
      tool,
      index,
      at: Math.min(Math.max(tool.at ?? 0, 0), text.length),
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
