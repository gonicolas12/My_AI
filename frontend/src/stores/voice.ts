/*
 * Voix : saisie (micro, Whisper) et lecture (synthèse du système), côté
 * Python (interfaces/desktop/voice.py). La fenêtre démarre, arrête et affiche
 * l'état, reçu en événements (voice.input, voice.transcript, voice.output).
 */

import { create } from 'zustand';

import { api } from '../lib/api';
import type { VoiceInputState, VoiceOutputState } from '../lib/events';
import { t } from '../i18n';
import { notify } from './app';

interface VoiceState {
  inputState: VoiceInputState;
  outputState: VoiceOutputState;
  /** Réponse en cours de lecture */
  speakingKey: string | null;
  /** Lecture automatique des réponses (ui.tts_autoread) */
  autoread: boolean;
}

export const useVoice = create<VoiceState>()(() => ({
  inputState: 'idle',
  outputState: 'idle',
  speakingKey: null,
  autoread: false,
}));

function errorText(error: unknown): string {
  return error instanceof Error ? error.message : String(error);
}

/** État relu au démarrage et à chaque reconnexion */
export async function loadVoiceStatus(): Promise<void> {
  try {
    const status = await api.voiceStatus();
    useVoice.setState({
      inputState: status.input_state,
      outputState: status.output_state,
      speakingKey: status.speaking_key,
      autoread: status.autoread,
    });
  } catch {
    // serveur injoignable : la reconnexion relira l'état
  }
}

export function applyVoiceInput(state: VoiceInputState, message: string): void {
  useVoice.setState({ inputState: state });
  if (state === 'error' && message) notify('error', message);
}

export function applyVoiceOutput(
  state: VoiceOutputState,
  key: string | null,
  message: string,
): void {
  useVoice.setState({ outputState: state, speakingKey: state === 'speaking' ? key : null });
  if (state === 'error' && message) notify('error', message);
}

// ── Saisie vocale ───────────────────────────────────────────────────────────

let transcriptTarget: ((text: string) => void) | null = null;

/** Zone de saisie qui recevra le texte dicté (celle dont on a cliqué le micro) */
export function setTranscriptTarget(target: ((text: string) => void) | null): void {
  transcriptTarget = target;
}

/** Texte dicté reçu du serveur : inséré au curseur de la zone qui l'attend */
export function applyTranscript(text: string): void {
  transcriptTarget?.(text);
}

/** Micro : démarre l'enregistrement, ou l'arrête (la transcription suit) */
export async function toggleDictation(target: (text: string) => void): Promise<void> {
  setTranscriptTarget(target);
  try {
    const { state } = await api.toggleDictation();
    useVoice.setState({ inputState: state });
  } catch (error) {
    notify('error', errorText(error));
  }
}

// ── Lecture vocale ──────────────────────────────────────────────────────────

/** Bouton de lecture d'une réponse : lit, ou arrête sa lecture */
export async function toggleSpeak(text: string, key: string): Promise<void> {
  try {
    await api.speak(text, key);
  } catch (error) {
    notify('error', errorText(error));
  }
}

export async function setAutoread(enabled: boolean): Promise<void> {
  try {
    const { autoread } = await api.setAutoread(enabled);
    useVoice.setState({ autoread });
    notify(
      autoread ? 'success' : 'info',
      autoread ? t('voice.autoreadOn') : t('voice.autoreadOff'),
    );
  } catch (error) {
    notify('error', errorText(error));
  }
}
