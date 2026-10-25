/*
 * Écran de chargement : la fenêtre s'affiche tout de suite, puis nomme
 * l'étape du lancement en cours (interfaces/desktop/lifecycle.py, _launch),
 * jusqu'à « prêt ». Ollama arrêté ou lancement en échec : l'erreur s'affiche
 * ici au lieu de laisser l'écran tourner. Au premier lancement, l'assistant de
 * configuration prend sa place jusqu'à ce que le lancement reprenne.
 */

import { Check, CircleAlert, LoaderCircle } from 'lucide-react';

import { RobotLogo } from '../../components/ui/RobotLogo';
import { type MessageKey, useT } from '../../i18n';
import { cn } from '../../lib/cn';
import type { EngineStatus } from '../../lib/events';
import type { ConnectionState } from '../../lib/ws';
import { OnboardingWizard } from '../onboarding/OnboardingWizard';

/** Étapes du lanceur, dans l'ordre de lifecycle.py */
const LAUNCH_STEPS: { id: string; label: MessageKey }[] = [
  { id: 'prefetch', label: 'loading.step.prefetch' },
  { id: 'ollama', label: 'loading.step.ollama' },
  { id: 'onboarding', label: 'loading.step.onboarding' },
  { id: 'model', label: 'loading.step.model' },
  { id: 'placement', label: 'loading.step.placement' },
  { id: 'engine', label: 'loading.step.engine' },
  { id: 'services', label: 'loading.step.services' },
];

interface LoadingScreenProps {
  status: EngineStatus | null;
  connection: ConnectionState;
}

export function LoadingScreen({ status, connection }: LoadingScreenProps) {
  const t = useT();
  const currentIndex = status ? LAUNCH_STEPS.findIndex((step) => step.id === status.step) : -1;
  const failed = status?.state === 'error';
  const ollamaDown = status?.ollama === false && Boolean(status.error);
  const connecting = connection !== 'open' || !status;

  // Premier lancement : le lancement attend l'assistant de configuration
  if (status?.state === 'onboarding' && connection === 'open') return <OnboardingWizard />;

  return (
    <div
      className="flex h-full flex-col items-center justify-center bg-bg px-6"
      role="status"
      aria-live="polite"
    >
      <RobotLogo size={64} className={cn('text-accent', !failed && 'pulse-soft')} />
      <h1 className="mt-4 text-2xl font-bold">My_AI</h1>
      <p className="mt-2 h-5 text-sm text-fg-2">
        {connecting ? t('loading.connecting') : (status?.label ?? '')}
      </p>

      <ol className="mt-8 w-full max-w-sm space-y-2.5">
        {LAUNCH_STEPS.map((step, index) => {
          const done = currentIndex > index || status?.state === 'ready';
          const current = currentIndex === index && !failed;
          const stepFailed = failed && currentIndex === index;
          return (
            <li key={step.id} className="flex items-start gap-3 text-sm">
              <span className="mt-0.5 flex h-4 w-4 shrink-0 items-center justify-center">
                {done ? (
                  <Check size={15} className="text-success" />
                ) : stepFailed ? (
                  <CircleAlert size={15} className="text-error" />
                ) : current ? (
                  <LoaderCircle size={15} className="spin text-accent" />
                ) : (
                  <span className="h-1.5 w-1.5 rounded-full bg-line-2" />
                )}
              </span>
              <span className="min-w-0 flex-1">
                <span className={cn(done || current ? 'text-fg' : 'text-fg-3')}>
                  {t(step.label)}
                </span>
                {current && status?.detail ? (
                  <span className="mt-0.5 block truncate text-xs text-fg-2" title={status.detail}>
                    {status.detail}
                  </span>
                ) : null}
              </span>
            </li>
          );
        })}
      </ol>

      {(failed || ollamaDown) && status?.error ? (
        <div className="mt-8 flex w-full max-w-md items-start gap-2 rounded-md border border-error/50 bg-error-soft px-3 py-2.5 text-sm">
          <CircleAlert size={16} className="mt-0.5 shrink-0 text-error" />
          <span>{status.error}</span>
        </div>
      ) : null}
    </div>
  );
}
