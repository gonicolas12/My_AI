/*
 * Lignes de pièces jointes ajoutées au texte d'un message (« 📎 rapport.pdf »,
 * « 🖼️ photo.png ») : format de l'interface Tk, gardé dans les sessions
 * (cf. bubble_text et split_attachments dans core/chat_service.py). La fenêtre
 * les affiche en puces, à part du texte.
 */

const ATTACH_LINE = /^(?:📎|🖼️|🖼)\s+\S/u;

export function splitAttachmentLines(text: string): { body: string; lines: string[] } {
  const lines = (text ?? '').split('\n');
  const attached: string[] = [];
  for (;;) {
    const last = lines[lines.length - 1];
    if (last === undefined || !ATTACH_LINE.test(last)) break;
    attached.unshift(last);
    lines.pop();
  }
  return { body: lines.join('\n').trimEnd(), lines: attached };
}
