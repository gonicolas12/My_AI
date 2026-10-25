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
  Globe,
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
import { localeInfo, setLocale, t as translate, useT } from '../../../i18n';
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
  label: ReactNode;
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

/**
 * Langue de l'interface (à chaud) et langue par défaut des réponses du modèle :
 * chaque langue porte son propre nom, lisible quelle que soit celle affichée
 */
function LanguageSection({ settings }: { settings: SettingsView }) {
  const t = useT();
  const [language, setLanguage] = useState(settings.language);
  const languageId = useId();

  const saveLanguage = async (value: string) => {
    const previous = language;
    setLanguage(value);
    try {
      await api.setLanguage(value);
      await setLocale(value);
      notify('success', translate('settings.language.saved'));
    } catch (error) {
      setLanguage(previous);
      notify('error', t('common.errorWith', { error: errorText(error) }));
    }
  };

  return (
    <Section title={t('settings.language.title')}>
      <Row
        htmlFor={languageId}
        label={
          <span className="inline-flex items-center gap-2">
            <Globe size={15} className="shrink-0 text-accent" />
            {t('settings.language.label')}
          </span>
        }
      >
        <select
          id={languageId}
          value={language}
          onChange={(event) => void saveLanguage(event.target.value)}
          className={cn(inputClass, 'w-48')}
        >
          {settings.languages.map((code) => (
            <option key={code} value={code}>
              {localeInfo(code).code === code ? localeInfo(code).name : code}
            </option>
          ))}
        </select>
      </Row>
      <Caption>{t('settings.language.caption')}</Caption>
    </Section>
  );
}

function ModelsSection() {
  const t = useT();
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
      notify('info', t('settings.models.enterName'));
      return;
    }
    void run('pull', name);
  };

  return (
    <Section title={t('settings.models.title')}>
      <p className="text-sm" role="status">
        {models === null ? (
          <span className="inline-flex items-center gap-2 text-fg-2">
            <LoaderCircle size={14} className="spin text-accent" /> {t('settings.models.checking')}
          </span>
        ) : models.ollama ? (
          <span className="inline-flex items-center gap-2 text-success">
            <CircleCheck size={15} /> {t('settings.models.active')}
          </span>
        ) : (
          <span className="inline-flex items-center gap-2 text-warning">
            <CircleAlert size={15} /> {t('settings.models.missing')}
          </span>
        )}
      </p>
      <Row label={t('settings.models.base')} htmlFor={baseId}>
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
        {t('settings.models.installed', {
          list: models?.installed.length ? models.installed.join(', ') : t('common.none'),
        })}
      </p>
      <Row label={t('settings.models.download')} htmlFor={pullId}>
        <input
          id={pullId}
          value={pullName}
          onChange={(event) => setPullName(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter') pull();
          }}
          placeholder={t('settings.models.downloadPlaceholder')}
          spellCheck={false}
          disabled={busy}
          className={cn(inputClass, 'w-48')}
        />
        <Button size="sm" onClick={pull} disabled={busy || !models?.ollama}>
          <Download size={15} /> {t('settings.models.pull')}
        </Button>
      </Row>
      {job ? (
        <div>
          <div
            className="h-1.5 overflow-hidden rounded-full bg-bg-3"
            role="progressbar"
            aria-label={t('settings.models.progress')}
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
            aria-label={t('settings.models.log')}
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
          {t('settings.models.apply')}
        </Button>
        <Caption>{t('settings.models.applyCaption')}</Caption>
      </div>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={t('settings.models.applyTitle')}
        message={t('settings.models.applyMessage', { base })}
        confirmLabel={t('settings.models.applyConfirm')}
        onConfirm={() => void run('apply', base)}
      />
    </Section>
  );
}

function GenerationSection({ settings }: { settings: SettingsView }) {
  const t = useT();
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
      notify('error', t('common.errorWith', { error: errorText(error) }));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Section title={t('settings.generation.title')}>
      <Row label={t('settings.generation.temperature')} htmlFor={temperatureId}>
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
        <span className="w-10 text-end font-mono text-sm tabular-nums">
          {temperature.toFixed(2)}
        </span>
      </Row>
      <Row label={t('settings.generation.numCtx')} htmlFor={numCtxId}>
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
      <Row label={t('settings.generation.timeout')} htmlFor={timeoutId}>
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
          <Save size={15} /> {t('settings.generation.save')}
        </Button>
        <Caption>{t('settings.generation.caption')}</Caption>
      </div>
    </Section>
  );
}

function OtherSection({ settings }: { settings: SettingsView }) {
  const t = useT();
  const autoread = useVoice((state) => state.autoread);
  const [relayAuto, setRelayAuto] = useState(settings.relay_auto_start);
  const [confirming, setConfirming] = useState(false);
  const autoreadId = useId();
  const relayId = useId();

  const saveAutoread = async (value: boolean) => {
    await setAutoread(value);
    notify('success', t('settings.autoread.saved'));
  };

  const saveRelayAuto = async (value: boolean) => {
    setRelayAuto(value);
    try {
      await api.setSettingFlag('relay.auto_start', value);
      notify('success', t('settings.relay.saved'));
    } catch (error) {
      setRelayAuto(!value);
      notify('error', t('common.errorWith', { error: errorText(error) }));
    }
  };

  const restartWizard = async () => {
    try {
      await api.restartOnboarding();
    } catch (error) {
      notify('error', t('common.errorWith', { error: errorText(error) }));
    }
  };

  return (
    <Section title={t('settings.other.title')}>
      <div className="flex items-center gap-3">
        <Switch
          id={autoreadId}
          checked={autoread}
          onCheckedChange={(value) => void saveAutoread(value)}
          label={t('settings.autoread.label')}
        />
        <label htmlFor={autoreadId} className="text-sm">
          {t('settings.autoread.label')}
        </label>
      </div>
      <div>
        <div className="flex items-center gap-3">
          <Switch
            id={relayId}
            checked={relayAuto}
            onCheckedChange={(value) => void saveRelayAuto(value)}
            label={t('settings.relay.label')}
          />
          <label htmlFor={relayId} className="text-sm">
            {t('settings.relay.label')}
          </label>
        </div>
        <Caption>
          <span className="ms-12 inline-block">{t('settings.relay.caption')}</span>
        </Caption>
      </div>
      <div className="space-y-1 border-t border-line pt-4">
        <Button onClick={() => setConfirming(true)}>
          <RefreshCw size={15} /> {t('settings.wizard.restart')}
        </Button>
        <Caption>{t('settings.wizard.caption')}</Caption>
      </div>
      <ConfirmDialog
        open={confirming}
        onOpenChange={setConfirming}
        title={t('settings.wizard.title')}
        message={t('settings.wizard.message')}
        confirmLabel={t('settings.wizard.confirm')}
        onConfirm={() => void restartWizard()}
      />
    </Section>
  );
}

export default function SettingsPanel() {
  const t = useT();
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
      title={t('settings.title')}
      description={t('settings.description')}
      width={760}
    >
      {settings ? <LanguageSection settings={settings} /> : null}
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
          <Sparkles size={14} className="pulse-soft text-accent" /> {t('settings.reading')}
        </p>
      )}
    </PanelDialog>
  );
}
