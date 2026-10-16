import { useEffect } from 'react';

import { useChat } from '../../stores/chat';
import { toggleSpeak, useVoice } from '../../stores/voice';

/**
 * Lecture automatique (ui.tts_autoread) : chaque réponse qui vient de
 * s'écrire est lue à voix haute, comme dans Tk ; jamais les réponses d'une
 * conversation rouverte. Active quelle que soit la page affichée.
 */
export function useAutoRead(): void {
  useEffect(
    () =>
      useChat.subscribe((state, previous) => {
        const finished = previous.live;
        if (!finished || state.live || !useVoice.getState().autoread) return;
        const message = state.messages[state.messages.length - 1];
        if (!message || message.mid !== finished.mid || message.role !== 'assistant') return;
        if (message.error || message.interrupted || !message.text.trim()) return;
        void toggleSpeak(message.text, message.mid);
      }),
    [],
  );
}
