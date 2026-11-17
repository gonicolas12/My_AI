/*
 * Mémoire : documents ajoutés pas encore rangés (événement memory.jobs),
 * révision du contenu (memory.changed), que le panneau ouvert relit,
 * question en cours : que faire de fichiers ou dossiers remis alors qu'un
 * autre porte déjà leur nom ? Et document ou dossier à montrer, cité dans une
 * réponse du chat.
 */

import { create } from 'zustand';

import type { ExistingDocuments } from '../lib/api';
import type { MemoryJob } from '../lib/events';
import { openPanel } from './panels';

/** Fichiers et dossiers déjà en mémoire sous ce nom (avec leur date) */
export type UpdateQuestion = ExistingDocuments;

/**
 * Réponse : les mettre à jour (remplacer le plus récent du même nom), garder les
 * deux (les ajouter à côté), ou ne pas les envoyer
 */
export type UpdateChoice = 'update' | 'keep' | 'cancel';

interface PendingUpdate extends UpdateQuestion {
  resolve: (choice: UpdateChoice) => void;
}

interface MemoryState {
  /** Documents ajoutés pas encore rangés, dans l'ordre de lecture */
  jobs: MemoryJob[];
  /** Augmente à chaque changement venu du serveur : le panneau ouvert se relit */
  revision: number;
  /** Des fichiers sont glissés au-dessus de la fenêtre : l'onglet Documents s'éclaire */
  dropping: boolean;
  /** Question affichée par le panneau : les mettre à jour, ou garder les deux ? */
  update: PendingUpdate | null;
  /** Nom d'un document ou d'un dossier cité dans le chat : le panneau s'ouvre sur lui */
  focus: string | null;
}

export const useMemory = create<MemoryState>()(() => ({
  jobs: [],
  revision: 0,
  dropping: false,
  update: null,
  focus: null,
}));

/**
 * Lien du chat vers un document ou un dossier de la Mémoire : le panneau
 * s'ouvre sur l'onglet Documents, cherché sur ce nom, ses dossiers dépliés
 */
export function showInMemory(name: string): void {
  useMemory.setState({ focus: name });
  openPanel('memory');
}

/** Le panneau a pris le nom à montrer : la prochaine ouverture repart des Faits */
export function clearMemoryFocus(): void {
  if (useMemory.getState().focus !== null) useMemory.setState({ focus: null });
}

/** File des documents ajoutés (événement memory.jobs, ou page relue) */
export function applyMemoryJobs(jobs: MemoryJob[]): void {
  useMemory.setState({ jobs });
}

/** Un onglet a changé (événement memory.changed) */
export function applyMemoryChanged(): void {
  useMemory.setState((state) => ({ revision: state.revision + 1 }));
}

export function setMemoryDropping(dropping: boolean): void {
  if (useMemory.getState().dropping !== dropping) useMemory.setState({ dropping });
}

// Une question à la fois : celles d'un second dépôt attendent la réponse à la première
let questions: Promise<unknown> = Promise.resolve();

/**
 * Demande quoi faire de fichiers ou dossiers déjà en mémoire sous ce nom ; le
 * panneau Mémoire affiche la question (answerUpdate y répond)
 */
export function askUpdate(question: UpdateQuestion): Promise<UpdateChoice> {
  const answer = questions.then(
    () =>
      new Promise<UpdateChoice>((resolve) => {
        useMemory.setState({ update: { ...question, resolve } });
      }),
  );
  questions = answer;
  return answer;
}

/** Réponse à la question en cours */
export function answerUpdate(choice: UpdateChoice): void {
  const pending = useMemory.getState().update;
  if (!pending) return;
  useMemory.setState({ update: null });
  pending.resolve(choice);
}
