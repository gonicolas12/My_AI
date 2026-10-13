/*
 * Actions de l'utilisateur : envoyées par le WebSocket quand il est ouvert,
 * sinon par l'API REST. Un refus du serveur (réponse en cours, message vide…)
 * s'affiche en notification, avec son texte.
 */

import { notify, useApp } from '../stores/app';
import { api } from './api';
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

let uiTimer: ReturnType<typeof setTimeout> | null = null;

export function setSidebarOpen(open: boolean): void {
  useApp.setState({ sidebarOpen: open });
  // Retenu d'un lancement à l'autre (data/.desktop_state.json)
  if (uiTimer) clearTimeout(uiTimer);
  uiTimer = setTimeout(() => {
    void api.saveUiState({ sidebar_open: open }).catch(() => undefined);
  }, 400);
}

export function toggleSidebar(): void {
  setSidebarOpen(!useApp.getState().sidebarOpen);
}
