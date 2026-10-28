/*
 * Page Code : la conversation de l'extension VS Code, partagée avec la vue
 * Code du téléphone (relay/code_hub.py, interfaces/desktop/code.py).
 *
 * L'état de VS Code (connecté, dossiers, réponse en cours) est lu au lancement
 * et suivi tout le temps : le bouton Code de la barre latérale le montre. Les
 * messages sont lus à l'ouverture de la page, puis suivis par les événements
 * « code.* » (codeReducer.ts). Un message tapé ici part à l'extension, qui
 * agit dans son workspace : la réponse arrive en streaming, ici comme dans
 * VS Code et sur le téléphone. Ses pièces jointes (celles du chat) sont
 * vérifiées par le serveur, gardées ici et envoyées avec lui.
 */

import { create } from 'zustand';

import { api, type CheckedAttachments } from '../lib/api';
import type { AnyCodeEvent, ApprovalDecision, RunAttachment } from '../lib/events';
import { notify } from './app';
import { applyCodeEvent, EMPTY_CODE, withSnapshot, type CodeConversation } from './codeReducer';

/** Pièce jointe du prochain message */
export interface CodeAttachment extends RunAttachment {
  id: string;
}

interface CodeStore extends CodeConversation {
  /** Message en cours de saisie : il survit aux changements d'onglet, ses pièces jointes aussi */
  draft: string;
  attachments: CodeAttachment[];
  /** Des fichiers survolent la fenêtre : la carte de saisie s'éclaire */
  dropping: boolean;
  /** Envoi parti, réponse du serveur attendue */
  sending: boolean;
  /** Demandes de retour en bas du fil (message envoyé d'ici) */
  follow: number;
}

const initialState: CodeStore = {
  ...EMPTY_CODE,
  draft: '',
  attachments: [],
  dropping: false,
  sending: false,
  follow: 0,
};

export const useCode = create<CodeStore>()(() => initialState);

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

// Événements reçus pendant une lecture de la conversation : appliqués après
// elle s'ils sont plus récents (ceux qu'elle contient déjà sont ignorés)
let reading: AnyCodeEvent[] | null = null;

/** Conversation entière (ouverture de la page, reconnexion) */
export async function loadCode(): Promise<void> {
  if (reading) return;
  reading = [];
  try {
    const snapshot = await api.code();
    const missed = reading;
    useCode.setState((state) => missed.reduce(applyCodeEvent, withSnapshot(state, snapshot)));
  } catch {
    // serveur injoignable : la reconnexion relira la conversation
  } finally {
    reading = null;
  }
}

/** État seul (lancement, page jamais ouverte) : le bouton Code de la barre latérale */
export async function loadCodeState(): Promise<void> {
  try {
    const { state, seq } = await api.codeState();
    useCode.setState((current) => (current.loaded || seq < current.seq ? {} : { state, seq }));
  } catch {
    // relu à la reconnexion
  }
}

/** Applique un lot d'événements « code.* » (un seul rendu par lot) */
export function applyCodeEvents(events: AnyCodeEvent[]): void {
  if (!events.length) return;
  reading?.push(...events);
  useCode.setState((state) => events.reduce(applyCodeEvent, state));
}

export function setCodeDraft(draft: string): void {
  useCode.setState({ draft });
}

let attachmentId = 0;

function addAttachments({ attachments, refused }: CheckedAttachments): void {
  for (const message of refused) notify('error', message);
  if (!attachments.length) return;
  useCode.setState((state) => {
    const known = new Set(state.attachments.map((item) => item.path.toLowerCase()));
    const added = attachments
      .filter((item) => !known.has(item.path.toLowerCase()))
      .map((item) => ({ ...item, id: `code-att-${++attachmentId}` }));
    return { attachments: [...state.attachments, ...added] };
  });
}

/** Fichiers choisis (dialogue) ou déposés, par leur chemin ; un dossier joint ses fichiers */
export async function addCodePaths(paths: string[]): Promise<void> {
  if (!paths.length) return;
  try {
    addAttachments(await api.codeAttachments(paths));
  } catch (error) {
    notify('error', errorText(error));
  }
}

/** Fichiers sans chemin (navigateur, image collée) : leur contenu part au serveur */
export async function uploadCodeFiles(files: File[], name?: string): Promise<void> {
  for (const file of files) {
    try {
      addAttachments(await api.uploadCodeAttachment(file, name ?? file.name));
    } catch (error) {
      notify('error', errorText(error));
    }
  }
}

export function setCodeDropping(dropping: boolean): void {
  useCode.setState({ dropping });
}

export function removeCodeAttachment(id: string): void {
  useCode.setState((state) => ({
    attachments: state.attachments.filter((item) => item.id !== id),
  }));
}

/**
 * Message et pièces jointes à l'extension VS Code ; faux s'il est refusé
 * (VS Code absent, réponse en cours)
 */
export async function sendCode(text: string): Promise<boolean> {
  const { attachments } = useCode.getState();
  useCode.setState((state) => ({ sending: true, follow: state.follow + 1 }));
  try {
    await api.sendCode(
      text,
      attachments.map(({ path, name }) => ({ path, name })),
    );
    // Parties avec ce message ; celles jointes pendant l'envoi restent
    const sent = new Set(attachments.map((item) => item.id));
    useCode.setState((state) => ({
      attachments: state.attachments.filter((item) => !sent.has(item.id)),
    }));
    return true;
  } catch (error) {
    notify('warning', errorText(error));
    return false;
  } finally {
    useCode.setState({ sending: false });
  }
}

/** Arrête la réponse en cours, qu'elle vienne d'ici, de VS Code ou du téléphone */
export async function stopCode(): Promise<void> {
  try {
    await api.stopCode();
  } catch (error) {
    notify('error', errorText(error));
  }
}

/** Nouvelle conversation, aussi dans VS Code et sur le téléphone */
export async function clearCode(): Promise<void> {
  try {
    await api.clearCode();
  } catch (error) {
    notify('error', errorText(error));
  }
}

/** Réponse à une demande d'approbation de l'extension (écriture, commande) */
export async function approveCode(callId: string, decision: ApprovalDecision): Promise<void> {
  try {
    await api.approveCode(callId, decision);
  } catch (error) {
    notify('error', errorText(error));
  }
}

/** Réservé aux tests */
export function resetCode(): void {
  useCode.setState(initialState, true);
}
