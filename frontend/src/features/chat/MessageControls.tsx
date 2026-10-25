/*
 * Actions au survol sous un message (§8) : lire à voix haute, noter,
 * régénérer, modifier. Copier est dans MessageActions.tsx.
 */

import { LoaderCircle, Mic, Pencil, RotateCcw, Square, Star, Volume2 } from 'lucide-react';
import { useState } from 'react';

import { IconButton } from '../../components/ui/Button';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { useT } from '../../i18n';
import { rateAnswer, regenerateAnswer } from '../../lib/actions';
import { cn } from '../../lib/cn';
import { toggleDictation, toggleSpeak, useVoice } from '../../stores/voice';

/** Lecture à voix haute d'une réponse ; le même bouton l'arrête */
export function SpeakButton({ text, mid }: { text: string; mid: string }) {
  const t = useT();
  const speaking = useVoice(
    (state) => state.outputState === 'speaking' && state.speakingKey === mid,
  );
  return (
    <IconButton
      label={speaking ? t('chat.speak.stop') : t('chat.speak.start')}
      size="sm"
      tooltipSide="bottom"
      onClick={() => void toggleSpeak(text, mid)}
      className={cn(speaking && 'text-accent hover:text-accent')}
    >
      {speaking ? <Square size={12} fill="currentColor" /> : <Volume2 size={15} />}
    </IconButton>
  );
}

/** Note de 1 à 5 étoiles (RLHF), figée une fois donnée comme dans Tk */
export function StarRating({ mid, rating }: { mid: string; rating?: number | undefined }) {
  const t = useT();
  const [hover, setHover] = useState(0);
  const [saving, setSaving] = useState(false);
  const rated = rating ?? 0;
  const shown = rated || hover;
  return (
    <div
      role="group"
      aria-label={rated ? t('chat.rating.rated', { rating: rated }) : t('chat.rating.rate')}
      title={rated ? t('chat.rating.ratedShort', { rating: rated }) : undefined}
      className="flex items-center"
      onMouseLeave={() => setHover(0)}
    >
      {[1, 2, 3, 4, 5].map((score) => (
        <button
          key={score}
          type="button"
          disabled={rated > 0 || saving}
          aria-label={t('chat.rating.stars', { count: score })}
          onMouseEnter={() => setHover(score)}
          onFocus={() => setHover(score)}
          onBlur={() => setHover(0)}
          onClick={() => {
            setSaving(true);
            void rateAnswer(mid, score).finally(() => setSaving(false));
          }}
          className="rounded-xs p-[3px] disabled:cursor-default"
        >
          <Star
            size={14}
            className={cn(
              'transition-colors duration-150',
              score <= shown ? 'fill-rating text-rating' : 'text-fg-3',
            )}
          />
        </button>
      ))}
    </div>
  );
}

/** Régénère la réponse (D5) : nouvelle variante ‹ k/n › du même message */
export function RegenerateButton({
  userMid,
  hasFollowing,
  busy,
}: {
  userMid: string;
  hasFollowing: boolean;
  busy: boolean;
}) {
  const t = useT();
  const [confirming, setConfirming] = useState(false);
  const run = () => void regenerateAnswer(userMid);
  return (
    <>
      <IconButton
        label={busy ? t('chat.regenerate.busy') : t('chat.regenerate.label')}
        size="sm"
        tooltipSide="bottom"
        disabled={busy}
        onClick={() => (hasFollowing ? setConfirming(true) : run())}
      >
        <RotateCcw size={15} />
      </IconButton>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={t('chat.regenerate.title')}
        message={t('chat.branchWarning')}
        confirmLabel={t('common.continue')}
        onConfirm={run}
      />
    </>
  );
}

/** Ouvre l'éditeur d'un message envoyé */
export function EditButton({ busy, onClick }: { busy: boolean; onClick: () => void }) {
  const t = useT();
  return (
    <IconButton
      label={busy ? t('chat.edit.busy') : t('chat.edit.label')}
      size="sm"
      tooltipSide="bottom"
      disabled={busy}
      onClick={onClick}
    >
      <Pencil size={14} />
    </IconButton>
  );
}

/** Micro de la zone de saisie : dictée transcrite par Whisper, insérée au curseur */
export function MicButton({ onTranscript }: { onTranscript: (text: string) => void }) {
  const t = useT();
  const state = useVoice((s) => s.inputState);
  const label =
    state === 'recording'
      ? t('chat.mic.stop')
      : state === 'transcribing'
        ? t('chat.mic.transcribing')
        : t('chat.mic.start');
  return (
    <IconButton
      label={label}
      tooltipSide="top"
      disabled={state === 'transcribing'}
      onClick={() => void toggleDictation(onTranscript)}
      className={cn(
        state === 'recording' && 'text-error hover:text-error',
        state === 'error' && 'text-error',
      )}
    >
      {state === 'transcribing' ? (
        <LoaderCircle size={17} className="spin text-accent" />
      ) : state === 'recording' ? (
        <span className="relative flex h-[17px] w-[17px] items-center justify-center">
          <span className="pulse-soft absolute h-3 w-3 rounded-full bg-error" />
        </span>
      ) : (
        <Mic size={17} />
      )}
    </IconButton>
  );
}
