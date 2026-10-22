/*
 * Bloc « 📚 **Sources** » qui termine une réponse appuyée sur une recherche
 * web (utils/citations.py) : retiré du texte affiché, il devient le bouton
 * « Sources » sous la réponse (SourcesButton). Le texte gardé, copié ou relu
 * par le modèle le contient toujours, et ses marqueurs [n] y trouvent leurs
 * liens (links.ts).
 */

export interface SourceLink {
  n: number;
  title: string;
  url: string;
  /** Nom d'hôte, pour l'icône du site */
  host: string;
}

export interface SplitSources {
  /** Texte à afficher, sans le bloc */
  body: string;
  sources: SourceLink[];
}

/** En-tête du bloc, seul sur sa ligne */
const HEADER = /(?:^|\n)[ \t]*📚[ \t]*(?:\*\*)?Sources(?:\*\*)?[ \t]*:?[ \t]*(?=\n|$)/gu;
/** Une source : « [n] [titre](url) » ou « [n] url » */
const ENTRY =
  /^[ \t]*\[(\d{1,3})\][ \t]*(?:\[([^\]]*)\]\((https?:\/\/[^)\s]+)\)|(https?:\/\/\S+))[ \t]*$/;

function hostOf(url: string): string {
  try {
    return new URL(url).hostname;
  } catch {
    return '';
  }
}

/** Texte affiché et sources du bloc final ; le texte entier s'il n'en a pas */
export function splitSources(text: string): SplitSources {
  let start = -1;
  let end = -1;
  for (const match of text.matchAll(HEADER)) {
    start = match.index;
    end = match.index + match[0].length;
  }
  if (start < 0) return { body: text, sources: [] };
  const lines = text.slice(end).split('\n');
  const sources: SourceLink[] = [];
  for (const [index, line] of lines.entries()) {
    if (!line.trim()) continue;
    const match = ENTRY.exec(line);
    if (match) {
      const url = match[3] ?? match[4] ?? '';
      const host = hostOf(url);
      sources.push({ n: Number(match[1]), title: match[2]?.trim() || host || url, url, host });
      continue;
    }
    // Dernière ligne encore en cours d'écriture (réponse streamée)
    if (index === lines.length - 1 && line.trimStart().startsWith('[')) continue;
    // Autre chose suit l'en-tête : ce n'est pas le bloc qui termine la réponse
    return { body: text, sources: [] };
  }
  return { body: text.slice(0, start).trimEnd(), sources };
}
