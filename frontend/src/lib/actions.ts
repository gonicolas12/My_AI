/*
 * Actions de l'utilisateur : envoyées par le WebSocket quand il est ouvert,
 * sinon par l'API REST. Un refus du serveur (réponse en cours, message vide…)
 * s'affiche en notification, avec son texte.
 */

import { notify, useApp } from '../stores/app';
import { api } from './api';
import { baseName } from './artifacts';
import type { ClientMessage } from './events';
import { getSocket } from './sync';
import { SocketError } from './ws';

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** Message par le WebSocket ; repli REST tant que la connexion se rétablit */
async function viaSocket(
  message: ClientMessage,
  fallback: () => Promise<unknown>,
): Promise<Record<string, unknown> | null> {
  const socket = getSocket();
  try {
    if (!socket) throw new SocketError('Connexion au serveur local en cours…', false);
    return await socket.send(message);
  } catch (error) {
    // Jamais parti : le passer par l'API REST. Parti puis connexion perdue :
    // pas de second envoi, il a peut-être été traité
    if (error instanceof SocketError && !error.sent) {
      await fallback();
      return null;
    }
    throw error;
  }
}

async function attempt<T>(action: () => Promise<T>, level: 'warning' | 'error' = 'warning') {
  try {
    return await action();
  } catch (error) {
    notify(level, errorText(error));
    return undefined;
  }
}

export async function sendMessage(text: string): Promise<boolean> {
  const result = await attempt(() =>
    viaSocket({ type: 'chat.send', text }, () => api.send({ text })),
  );
  return result !== undefined;
}

export async function stopGeneration(): Promise<void> {
  await attempt(() => viaSocket({ type: 'chat.stop' }, () => api.stop()));
}

export async function cancelQueued(requestId: string): Promise<void> {
  await attempt(() =>
    viaSocket({ type: 'chat.cancel', request_id: requestId }, () =>
      Promise.reject(new Error('Connexion au serveur local en cours…')),
    ),
  );
}

export async function answerConfirm(confirmId: string, accepted: boolean): Promise<void> {
  await attempt(() =>
    viaSocket({ type: 'confirm.response', confirm_id: confirmId, accepted }, () =>
      Promise.reject(new Error('Connexion au serveur local en cours…')),
    ),
  );
}

export async function newConversation(): Promise<void> {
  await attempt(() => api.newConversation());
}

export async function clearConversation(): Promise<void> {
  await attempt(() => api.clear());
}

export async function saveConversation(): Promise<void> {
  const result = await attempt(() => api.save());
  if (result && !result.saved) notify('info', 'Rien à sauvegarder : la conversation est vide.');
}

export async function openSession(id: string): Promise<void> {
  await attempt(() => api.loadSession(id));
}

export async function removeSession(id: string): Promise<void> {
  await attempt(() => api.deleteSession(id));
}

/** Note de 1 à 5 étoiles (RLHF) ; vrai si elle a été enregistrée */
export async function rateAnswer(mid: string, score: number): Promise<boolean> {
  const result = await attempt(() => api.rate(mid, score));
  return result !== undefined;
}

/** Document produit par l'appli → son application (les autres sont refusés) */
export async function openFile(path: string): Promise<void> {
  await attempt(() => api.openFile(path));
}

/** Chemin cité ou joint → Explorateur, fichier sélectionné ; jamais exécuté */
export async function revealPath(path: string): Promise<void> {
  await attempt(() => api.revealFile(path));
}

/** Document produit → copie dans Téléchargements (clic sur le nom dans Tk) */
export async function saveToDownloads(path: string): Promise<void> {
  const result = await attempt(() => api.downloadFile(path), 'error');
  if (result) {
    notify('success', `✅ Votre fichier ${baseName(path)} a été téléchargé dans : ${result.path}`);
  }
}

const uiTimers = new Map<string, ReturnType<typeof setTimeout>>();

/** Retient un état de l'interface d'un lancement à l'autre (data/.desktop_state.json) */
function saveUiState(key: 'sidebar_open' | 'preview_width', value: boolean | number): void {
  const previous = uiTimers.get(key);
  if (previous) clearTimeout(previous);
  uiTimers.set(
    key,
    setTimeout(() => {
      uiTimers.delete(key);
      void api.saveUiState({ [key]: value }).catch(() => undefined);
    }, 400),
  );
}

export function setSidebarOpen(open: boolean): void {
  useApp.setState({ sidebarOpen: open });
  saveUiState('sidebar_open', open);
}

export function savePreviewWidth(width: number): void {
  saveUiState('preview_width', width);
}

export function toggleSidebar(): void {
  setSidebarOpen(!useApp.getState().sidebarOpen);
}
