import { useEffect } from 'react';

import { messageArtifacts } from '../../lib/artifacts';
import { useChat } from '../../stores/chat';
import { closePreview, openPreview } from '../../stores/preview';

/** Le volet attend que la réponse ait fini sa mise en page (Tk : 120 ms) */
const OPEN_DELAY = 120;

/**
 * Ouverture automatique du volet d'aperçu, comme dans Tk et sur Claude web :
 * à la fin d'une réponse qui contient un artefact, une seule fois par réponse,
 * jamais à la réouverture d'une conversation. Changer de conversation ferme
 * le volet.
 */
export function useAutoOpenArtifacts(): void {
  useEffect(() => {
    const opened = new Set<string>();
    return useChat.subscribe((state, previous) => {
      if (previous.conversationId && state.conversationId !== previous.conversationId) {
        closePreview();
      }
      const finished = previous.live;
      if (!finished || state.live) return;
      const message = state.messages[state.messages.length - 1];
      if (!message || message.mid !== finished.mid || message.role !== 'assistant') return;
      if (message.error || message.interrupted || opened.has(message.mid)) return;
      const items = messageArtifacts(message.text, message.documents ?? []);
      if (!items.length) return;
      opened.add(message.mid);
      setTimeout(() => {
        // Toujours la même conversation : sinon le volet n'a plus lieu d'être
        if (useChat.getState().messages.some((item) => item.mid === message.mid)) {
          openPreview(message.mid, items, 0);
        }
      }, OPEN_DELAY);
    });
  }, []);
}
