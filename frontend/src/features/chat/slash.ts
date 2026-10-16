/*
 * Autocomplétion des slash commands (slash_commands.py de l'interface Tk) :
 * « / » en tout début de saisie ouvre la liste des commandes de la
 * bibliothèque de prompts qui commencent par le mot tapé (8 au plus).
 * Choisir une commande insère « /commande » : à l'envoi, le serveur la
 * déplie en prompt détaillé (PromptLibrary.expand).
 */

import { useEffect, useState } from 'react';

import { api, type SlashCommand } from '../../lib/api';

/** « / » en tout début de saisie, suivi d'un mot sans espace (_SLASH_RE) */
const SLASH = /^\/(\S*)$/;

/** Nombre maximal de suggestions (_MAX_ROWS) */
export const MAX_COMMANDS = 8;

/** Mot tapé après « / », ou null si la saisie n'est pas une commande en cours */
export function slashPrefix(draft: string): string | null {
  const match = SLASH.exec(draft);
  return match ? (match[1] ?? '') : null;
}

/** Texte inséré quand on choisit une commande */
export function commandText(command: SlashCommand): string {
  return command.command ? `/${command.command} ` : '';
}

/** Commandes correspondant à la saisie (vide tant qu'elle n'en est pas une) */
export function useSlashCommands(draft: string): SlashCommand[] {
  const prefix = slashPrefix(draft);
  const [found, setFound] = useState<{ prefix: string; commands: SlashCommand[] } | null>(null);

  useEffect(() => {
    if (prefix === null) return undefined;
    let alive = true;
    const timer = setTimeout(() => {
      api
        .slashCommands(prefix)
        .then(({ commands }) => {
          if (alive) setFound({ prefix, commands: commands.slice(0, MAX_COMMANDS) });
        })
        .catch(() => undefined);
    }, 40);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [prefix]);

  if (prefix === null || found?.prefix !== prefix) return [];
  return found.commands;
}
