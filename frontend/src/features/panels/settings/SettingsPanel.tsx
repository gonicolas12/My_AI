/*
 * Réglages (settings_panel.py de Tk) : modèles Ollama (liste, téléchargement,
 * modèle de base de my_ai), paramètres de génération, autres réglages
 * (langue, lecture automatique, Relay au lancement, assistant de
 * configuration). Les écritures dans config.yaml gardent ses commentaires
 * (interfaces/desktop/settings.py).
 */

import {
  CircleAlert,
  CircleCheck,
  Download,
  LoaderCircle,
  RefreshCw,
  Save,
  Settings,
  Sparkles,
} from 'lucide-react';
import { type ReactNode, useEffect, useId, useRef, useState } from 'react';

import { Button } from '../../../components/ui/Button';
import { ConfirmDialog } from '../../../components/ui/ConfirmDialog';
import { Switch } from '../../../components/ui/Switch';
import { ApiError, api, type ModelsView, type SettingsView } from '../../../lib/api';
import { cn } from '../../../lib/cn';
import { notify } from '../../../stores/app';
import {
  beginModelJob,
  failModelJob,
  loadModelJob,
  progressLabel,
  useModels,
} from '../../../stores/models';
import { closePanel } from '../../../stores/panels';
import { setAutoread, useVoice } from '../../../stores/voice';
import { PanelDialog } from '../PanelDialog';

const errorText = (error: unknown) => (error instanceof ApiError ? error.message : String(error));

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="border-b border-line pb-5 last:border-b-0 [&+&]:pt-5">
      <h3 className="mb-3.5 text-sm font-semibold tracking-wide text-accent uppercase">{title}</h3>
      <div className="space-y-3.5">{children}</div>
    </section>
  );
}

function Row({
  label,
  htmlFor,
  children,
}: {
  label: string;
  htmlFor?: string;
  children: ReactNode;
}) {
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2">
      <label htmlFor={htmlFor} className="w-56 shrink-0 text-sm text-fg-2">
        {label}
      </label>
      <div className="flex min-w-0 flex-1 items-center gap-2">{children}</div>
    </div>
  );
}

const Caption = ({ children }: { children: ReactNode }) => (
  <p className="text-xs text-fg-3">{children}</p>
);

const inputClass =
  'h-9 rounded-md border border-line bg-bg-3 px-2.5 text-sm text-fg placeholder:text-fg-3 disabled:text-fg-3';

function ModelsSection() {
  const [models, setModels] = useState<ModelsView | null>(null);
  const [base, setBase] = useState('');
  const [pullName, setPullName] = useState('');
  const [confirming, setConfirming] = useState(false);
  const job = useModels((state) =>
    state.job && state.job.action !== 'install' ? state.job : null,
  );
  const logRef = useRef<HTMLPreElement>(null);
  const baseId = useId();
  const pullId = useId();

  useEffect(() => {
    void loadModelJob();
  }, []);

  // Liste relue à l'ouverture, puis à la fin d'un téléchargement ou d'une régénération
  const finished = job && !job.running ? `${job.action}|${job.name}|${String(job.ok)}` : '';
  useEffect(() => {
    let alive = true;
    api
      .settingsModels()
      .then((fresh) => {
        if (!alive) return;
        setModels(fresh);
        setBase((current) =>
          current && fresh.bases.includes(current) ? current : fresh.base_model,
        );
      })
      .catch(() => {
        if (alive) setModels({ ollama: false, installed: [], bases: [], base_model: '' });
      });
    return () => {
      alive = false;
    };
  }, [finished]);

  useEffect(() => {
    logRef.current?.scrollTo({ top: logRef.current.scrollHeight });
  }, [job?.log.length]);

  const busy = Boolean(job?.running);
  const run = async (action: 'pull' | 'apply', name: string) => {
    beginModelJob(action, name);
    try {
      await (action === 'pull' ? api.pullModel(name) : api.applyModel(name));
    } catch (error) {
      failModelJob(errorText(error));
      notify('warning', errorText(error));
    }
  };

  const pull = () => {
    const name = pullName.trim();
    if (!name) {
      notify('info', 'Entrez un nom de modèle (ex : qwen3.5:4b).');
      return;
    }
    void run('pull', name);
  };

  return (
    <Section title="Modèles Ollama">
      <p className="text-sm" role="status">
        {models === null ? (
          <span className="inline-flex items-center gap-2 text-fg-2">
            <LoaderCircle size={14} className="spin text-accent" /> Vérification d'Ollama…
          </span>
        ) : models.ollama ? (
          <span className="inline-flex items-center gap-2 text-success">
            <CircleCheck size={15} /> Ollama actif
          </span>
        ) : (
          <span className="inline-flex items-center gap-2 text-warning">
            <CircleAlert size={15} /> Ollama non détecté — démarrez-le pour gérer les modèles
          </span>
        )}
      </p>
      <Row label="Modèle de base :" htmlFor={baseId}>
        <select
          id={baseId}
          value={base}
          onChange={(event) => setBase(event.target.value)}
          disabled={!models?.bases.length || busy}
          className={cn(inputClass, 'w-60')}
        >
          {(models?.bases ?? []).map((name) => (
            <option key={name} value={name}>
              {name}
            </option>
          ))}
        </select>
      </Row>
      <p className="text-xs text-fg-2">
        Modèles installés : {models?.installed.length ? models.installed.join(', ') : '(aucun)'}
      </p>
      <Row label="Télécharger :" htmlFor={pullId}>
        <input
          id={pullId}
          value={pullName}
          onChange={(event) => setPullName(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') pull();
          }}
          placeholder="ex : qwen3.5:4b"
          spellCheck={false}
          disabled={busy}
          className={cn(inputClass, 'w-48')}
        />
        <Button size="sm" onClick={pull} disabled={busy || !models?.ollama}>
          <Download size={15} /> Pull
        </Button>
      </Row>
      {job ? (
        <div>
          <div
            className="h-1.5 overflow-hidden rounded-full bg-bg-3"
            role="progressbar"
            aria-label="Progression"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(job.fraction * 100)}
          >
            <div
              className={cn(
                'h-full rounded-full transition-[width] duration-200',
                job.ok === false ? 'bg-error' : 'bg-accent',
              )}
              style={{ width: `${(job.ok && job.action === 'apply' ? 1 : job.fraction) * 100}%` }}
            />
          </div>
          <p className="mt-1.5 h-4 truncate text-xs text-fg-2">{progressLabel(job)}</p>
          <pre
            ref={logRef}
            aria-label="Journal"
            className="mt-1.5 max-h-28 min-h-16 overflow-y-auto rounded-md border border-line bg-bg px-3 py-2 font-mono text-xs leading-relaxed whitespace-pre-wrap text-fg-2"
          >
            {job.log.join('\n')}
          </pre>
        </div>
      ) : null}
      <div className="space-y-1">
        <Button
          variant="primary"
          onClick={() => setConfirming(true)}
          disabled={busy || !base || !models?.ollama}
        >
          {busy && job?.action === 'apply' ? (
            <LoaderCircle size={15} className="spin" />
          ) : (
            <CircleCheck size={15} />
          )}
          Appliquer (régénère le modèle 'my_ai')
        </Button>
        <Caption>Régénère proprement le modèle personnalisé (system prompt préservé).</Caption>
      </div>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title="Appliquer"
        message={`Régénérer le modèle 'my_ai' à partir de « ${base} » ? Le system prompt du Modelfile sera préservé.`}
        confirmLabel="Régénérer"
        onConfirm={() => void run('apply', base)}
      />
    </Section>
  );
}

function GenerationSection({ settings }: { settings: SettingsView }) {
  const [temperature, setTemperature] = useState(settings.generation.temperature);
  const [numCtx, setNumCtx] = useState(settings.generation.num_ctx);
  const [timeout, setTimeoutValue] = useState(String(settings.generation.timeout));
  const [saving, setSaving] = useState(false);
  const temperatureId = useId();
  const numCtxId = useId();
  const timeoutId = useId();

  const save = async () => {
    setSaving(true);
    try {
      // Saisie illisible : valeur par défaut, comme Tk
      const parsed = Number(timeout.replace(',', '.'));
      const saved = await api.saveGeneration({
        temperature,
        num_ctx: numCtx,
        timeout: Number.isFinite(parsed) && timeout.trim() ? parsed : 1200,
      });
      setTimeoutValue(String(saved.timeout));
      setTemperature(saved.temperature);
    } catch (error) {
      notify('error', `❌ Erreur : ${errorText(error)}`);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Section title="Paramètres généraux">
      <Row label="Température :" htmlFor={temperatureId}>
        <input
          id={temperatureId}
          type="range"
          min={0}
          max={1}
          step={0.05}
          value={temperature}
          onChange={(event) => setTemperature(Number(event.target.value))}
          className="w-56 accent-[var(--accent)]"
        />
        <span className="w-10 text-right font-mono text-sm tabular-nums">
          {temperature.toFixed(2)}
        </span>
      </Row>
      <Row label="Fenêtre de contexte (num_ctx) :" htmlFor={numCtxId}>
        <select
          id={numCtxId}
          value={numCtx}
          onChange={(event) => setNumCtx(Number(event.target.value))}
          className={cn(inputClass, 'w-32')}
        >
          {settings.num_ctx_choices.map((value) => (
            <option key={value} value={value}>
              {value}
            </option>
          ))}
        </select>
      </Row>
      <Row label="Timeout requête LLM (s) :" htmlFor={timeoutId}>
        <input
          id={timeoutId}
          type="number"
          min={30}
          max={7200}
          value={timeout}
          onChange={(event) => setTimeoutValue(event.target.value)}
          className={cn(inputClass, 'w-28')}
        />
      </Row>
      <div className="space-y-1">
        <Button onClick={() => void save()} disabled={saving}>
          <Save size={15} /> Enregistrer les paramètres
        </Button>
        <Caption>
          Écrit dans config.yaml + Modelfile (commentaires préservés) et applique immédiatement.
        </Caption>
      </div>
    </Section>
  );
}

function OtherSection({ settings }: { settings: SettingsView }) {
  const autoread = useVoice((state) => state.autoread);
  const [language, setLanguage] = useState(settings.language);
  const [relayAuto, setRelayAuto] = useState(settings.relay_auto_start);
  const [confirming, setConfirming] = useState(false);
  const languageId = useId();
  const autoreadId = useId();
  const relayId = useId();

  const saveLanguage = async (value: string) => {
    setLanguage(value);
    try {
      await api.setSettingFlag('language.default', value);
      notify('success', '💾 Langue enregistrée');
    } catch (error) {
      setLanguage(settings.language);
      notify('error', `❌ Erreur : ${errorText(error)}`);
    }
  };

  const saveAutoread = async (value: boolean) => {
    await setAutoread(value);
    notify('success', '💾 Lecture vocale enregistrée');
  };

  const saveRelayAuto = async (value: boolean) => {
    setRelayAuto(value);
    try {
      await api.setSettingFlag('relay.auto_start', value);
      notify('success', '💾 Relay auto-start enregistré');
    } catch (error) {
      setRelayAuto(!value);
      notify('error', `❌ Erreur : ${errorText(error)}`);
    }
  };

  const restartWizard = async () => {
    try {
      await api.restartOnboarding();
    } catch (error) {
      notify('error', `❌ Erreur : ${errorText(error)}`);
    }
  };

  return (
    <Section title="Autres réglages">
      <Row label="Langue par défaut :" htmlFor={languageId}>
        <select
          id={languageId}
          value={language}
          onChange={(event) => void saveLanguage(event.target.value)}
          className={cn(inputClass, 'w-24')}
        >
          {settings.languages.map((code) => (
            <option key={code} value={code}>
              {code}
            </option>
          ))}
        </select>
      </Row>
      <div className="flex items-center gap-3">
        <Switch
          id={autoreadId}
          checked={autoread}
          onCheckedChange={(value) => void saveAutoread(value)}
          label="Lecture vocale automatique des réponses"
        />
        <label htmlFor={autoreadId} className="text-sm">
          Lecture vocale automatique des réponses
        </label>
      </div>
      <div>
        <div className="flex items-center gap-3">
          <Switch
            id={relayId}
            checked={relayAuto}
            onCheckedChange={(value) => void saveRelayAuto(value)}
            label="Démarrer le Relay au lancement"
          />
          <label htmlFor={relayId} className="text-sm">
            Démarrer le Relay au lancement
          </label>
        </div>
        <Caption>
          <span className="ml-12 inline-block">
            (Le Relay auto-start prend effet au prochain démarrage.)
          </span>
        </Caption>
      </div>
      <div className="space-y-1 border-t border-line pt-4">
        <Button onClick={() => setConfirming(true)}>
          <RefreshCw size={15} /> Relancer l'assistant de configuration
        </Button>
        <Caption>Supprime le marqueur ; l'assistant s'affichera au prochain démarrage.</Caption>
      </div>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title="Relancer l'assistant"
        message="Relancer l'assistant de configuration au prochain démarrage ?"
        confirmLabel="Relancer"
        onConfirm={() => void restartWizard()}
      />
    </Section>
  );
}

export default function SettingsPanel() {
  const [settings, setSettings] = useState<SettingsView | null>(null);
  const [failed, setFailed] = useState('');

  useEffect(() => {
    api
      .settings()
      .then(setSettings)
      .catch((error: unknown) => setFailed(errorText(error)));
  }, []);

  return (
    <PanelDialog
      open
      onOpenChange={(open) => {
        if (!open) closePanel();
      }}
      icon={Settings}
      title="Réglages"
      description="Modèle local, paramètres de génération et préférences de My_AI."
      width={760}
    >
      <ModelsSection />
      {settings ? (
        <>
          <GenerationSection settings={settings} />
          <OtherSection settings={settings} />
        </>
      ) : failed ? (
        <p className="pt-5 text-sm text-error">{failed}</p>
      ) : (
        <p className="inline-flex items-center gap-2 pt-5 text-sm text-fg-2">
          <Sparkles size={14} className="pulse-soft text-accent" /> Lecture des réglages…
        </p>
      )}
    </PanelDialog>
  );
}
