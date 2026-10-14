/*
 * Assistant de premier lancement (OnboardingWizard d'interfaces/onboarding.py),
 * dans la fenêtre : le lancement l'attend, à son étape, avant la vérification
 * de my_ai et le placement du modèle (interfaces/desktop/lifecycle.py).
 *
 * Ollama, matériel et modèle recommandé ; « Installer » télécharge le modèle
 * choisi et crée my_ai (progression et journal en direct), « Passer » marque
 * l'assistant comme fait. Après une erreur : « Réessayer » ou « Continuer
 * quand même » ; après l'installation : « Démarrer My_AI ».
 */

import {
  CircleAlert,
  CircleCheck,
  Cpu,
  LoaderCircle,
  MemoryStick,
  MonitorCog,
  RefreshCw,
  Rocket,
} from 'lucide-react';
import { useCallback, useEffect, useRef, useState } from 'react';

import { Button } from '../../components/ui/Button';
import { RobotLogo } from '../../components/ui/RobotLogo';
import { ApiError, api, type OnboardingInfo } from '../../lib/api';
import { cn } from '../../lib/cn';
import { beginModelJob, failModelJob, progressLabel, useModels } from '../../stores/models';

/** « 15.7 » → « 15,7 Go » ; inconnue sinon (Tk) */
function gigabytes(value: number | null): string {
  return value === null ? 'inconnue' : `${String(value).replace('.', ',')} Go`;
}

function HardwareLine({ info }: { info: OnboardingInfo }) {
  return (
    <p className="flex flex-wrap items-center justify-center gap-x-3 gap-y-1 text-sm text-fg-2">
      <span className="inline-flex items-center gap-1.5">
        <MemoryStick size={15} /> RAM : {gigabytes(info.ram_gb)}
      </span>
      <span aria-hidden="true">·</span>
      {info.vram_gb !== null ? (
        <span className="inline-flex items-center gap-1.5">
          <MonitorCog size={15} /> VRAM GPU : {gigabytes(info.vram_gb)}
        </span>
      ) : (
        <span className="inline-flex items-center gap-1.5">
          <Cpu size={15} />
          {info.cpu_cores !== null ? `${info.cpu_cores} cœurs` : 'CPU'}, pas de GPU dédié (inférence
          CPU)
        </span>
      )}
      <span aria-hidden="true">→</span>
      <span>
        recommandé : <strong className="font-semibold text-fg">{info.recommended}</strong>
      </span>
    </p>
  );
}

export function OnboardingWizard() {
  const [info, setInfo] = useState<OnboardingInfo | null>(null);
  const [checking, setChecking] = useState(true);
  const [model, setModel] = useState('');
  const [leaving, setLeaving] = useState(false);
  const job = useModels((state) => (state.job?.action === 'install' ? state.job : null));
  const logRef = useRef<HTMLPreElement>(null);

  const refresh = useCallback(async () => {
    setChecking(true);
    try {
      const fresh = await api.onboarding();
      setInfo(fresh);
      setModel((current) => current || fresh.recommended);
      // Fenêtre rechargée pendant l'installation : son état et son journal
      if (fresh.job?.action === 'install') useModels.setState({ job: fresh.job });
    } catch {
      // serveur injoignable : « Réessayer » reste possible
    } finally {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    let alive = true;
    api
      .onboarding()
      .then((fresh) => {
        if (!alive) return;
        setInfo(fresh);
        setModel(fresh.recommended);
        if (fresh.job?.action === 'install') useModels.setState({ job: fresh.job });
      })
      .catch(() => undefined)
      .finally(() => {
        if (alive) setChecking(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [job?.log.length]);

  const installing = Boolean(job?.running);
  const installed = job?.ok === true;
  const failed = job?.ok === false;
  const ollamaDown = info !== null && !info.ollama;

  const install = async () => {
    if (!model || installing) return;
    beginModelJob('install', model);
    try {
      await api.installModel(model);
    } catch (error) {
      const message = error instanceof ApiError ? error.message : String(error);
      // Ollama arrêté entre-temps : l'état d'Ollama se met à jour, rien n'a commencé
      if (message.includes('Ollama')) {
        useModels.setState({ job: null });
        void refresh();
      } else {
        failModelJob(message);
      }
    }
  };

  // Après une erreur : retour à « Installer », le journal reste (Tk)
  const retry = () =>
    useModels.setState((state) =>
      state.job ? { job: { ...state.job, ok: null, fraction: 0, status: '', message: '' } } : state,
    );

  const leave = async (action: 'skip' | 'finish') => {
    setLeaving(true);
    try {
      await (action === 'skip' ? api.skipOnboarding() : api.finishOnboarding());
    } catch {
      setLeaving(false);
    }
  };

  let primary;
  if (installed) {
    primary = (
      <Button variant="primary" onClick={() => void leave('finish')} disabled={leaving}>
        <CircleCheck size={16} /> Démarrer My_AI
      </Button>
    );
  } else if (failed) {
    primary = (
      <Button variant="primary" onClick={retry}>
        <RefreshCw size={16} /> Réessayer
      </Button>
    );
  } else if (ollamaDown) {
    primary = (
      <Button variant="primary" onClick={() => void refresh()} disabled={checking}>
        <RefreshCw size={16} className={cn(checking && 'spin')} /> Réessayer
      </Button>
    );
  } else {
    primary = (
      <Button
        variant="primary"
        onClick={() => void install()}
        disabled={installing || checking || !info}
      >
        {installing ? <LoaderCircle size={16} className="spin" /> : <Rocket size={16} />}
        {installing ? 'Installation…' : 'Installer'}
      </Button>
    );
  }

  return (
    <div className="flex h-full items-center justify-center overflow-y-auto bg-bg px-6 py-8">
      <section
        aria-labelledby="onboarding-title"
        className="w-full max-w-xl rounded-lg border border-line bg-bg-2 p-7 shadow-lg"
        style={{ animation: 'rise-in var(--motion) var(--motion-ease)' }}
      >
        <div className="flex flex-col items-center text-center">
          <RobotLogo size={52} className="text-accent" />
          <h1 id="onboarding-title" className="mt-3 text-2xl font-bold">
            Bienvenue dans My_AI
          </h1>
          <p className="mt-1.5 text-sm text-fg-2">
            Configurons votre modèle IA local en quelques clics.
          </p>
        </div>

        <div className="mt-6 space-y-3 text-center" role="status" aria-live="polite">
          {checking && !info ? (
            <p className="inline-flex items-center gap-2 text-sm text-fg-2">
              <LoaderCircle size={15} className="spin text-accent" /> Vérification d'Ollama…
            </p>
          ) : ollamaDown ? (
            <p className="inline-flex items-start gap-2 text-sm text-warning">
              <CircleAlert size={16} className="mt-0.5 shrink-0" />
              <span>
                Ollama non détecté — installez-le depuis{' '}
                <a href="https://ollama.com" className="underline underline-offset-2">
                  ollama.com
                </a>{' '}
                puis Réessayez
              </span>
            </p>
          ) : info ? (
            <p className="inline-flex items-center gap-2 text-sm text-success">
              <CircleCheck size={16} /> Ollama détecté et actif
            </p>
          ) : null}
          {info ? <HardwareLine info={info} /> : null}
        </div>

        <label className="mt-6 flex items-center justify-center gap-3 text-sm">
          <span className="text-fg-2">Modèle de base :</span>
          <select
            value={model}
            onChange={(event) => setModel(event.target.value)}
            disabled={installing || installed || !info}
            className="h-9 min-w-40 rounded-md border border-line bg-bg-3 px-2.5 text-sm text-fg disabled:text-fg-3"
          >
            {(info?.choices ?? []).map((choice) => (
              <option key={choice} value={choice}>
                {choice}
              </option>
            ))}
          </select>
        </label>

        {job ? (
          <div className="mt-6">
            <div
              className="h-1.5 overflow-hidden rounded-full bg-bg-3"
              role="progressbar"
              aria-valuemin={0}
              aria-valuemax={100}
              aria-valuenow={Math.round((installed ? 1 : job.fraction) * 100)}
            >
              <div
                className={cn(
                  'h-full rounded-full transition-[width] duration-200',
                  failed ? 'bg-error' : 'bg-accent',
                )}
                style={{ width: `${(installed ? 1 : job.fraction) * 100}%` }}
              />
            </div>
            <p className="mt-1.5 h-4 truncate text-xs text-fg-2">
              {installed ? 'Terminé — 100%' : progressLabel(job)}
            </p>
            <pre
              ref={logRef}
              aria-label="Journal de l'installation"
              className="mt-2 max-h-52 min-h-24 overflow-y-auto rounded-md border border-line bg-bg px-3 py-2 font-mono text-xs leading-relaxed whitespace-pre-wrap text-fg-2"
            >
              {job.log.join('\n')}
            </pre>
          </div>
        ) : null}

        <div className="mt-7 flex items-center justify-center gap-3">
          {primary}
          <Button
            variant="secondary"
            onClick={() => void leave('skip')}
            disabled={installing || installed || leaving}
          >
            {failed ? 'Continuer quand même' : 'Passer'}
          </Button>
        </div>
      </section>
    </div>
  );
}
