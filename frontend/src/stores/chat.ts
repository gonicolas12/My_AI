import { create } from 'zustand';

import type { ConversationSnapshot, ServerEvent } from '../lib/events';
import { type ChatState, fromSnapshot, initialChatState, reduceChat } from './chatReducer';

export const useChat = create<ChatState>()(() => initialChatState);

/** Applique un lot d'événements (un seul rendu par lot) */
export function applyChatEvents(events: ServerEvent[]): void {
  if (!events.length) return;
  useChat.setState((state) => events.reduce(reduceChat, state), true);
}

/** Remplace l'état par un instantané du serveur */
export function setChatSnapshot(snapshot: ConversationSnapshot): void {
  useChat.setState(fromSnapshot(snapshot), true);
}

export function resetChat(): void {
  useChat.setState(initialChatState, true);
}
