/*
 * Mode Débat entre deux agents (debate.py de Tk) : un proposant, un opposant,
 * le sujet et le nombre de tours (1 à 10, 3 par défaut). Le débat devient un
 * fil : un tour par section, le proposant puis l'opposant. Les messages de
 * Tk s'affichent sous les champs.
 */

import { useId, useState } from 'react';

import { Button } from '../../components/ui/Button';
import { Dialog } from '../../components/ui/Dialog';
import { useT } from '../../i18n';
import { errorText, startDebate, useAgents } from '../../stores/agents';

const fieldClass =
  'h-9 w-full rounded-md border border-line bg-bg px-2.5 text-sm text-fg outline-none focus:border-line-2 disabled:text-fg-3';

interface DebateDialogProps {
  onClose: () => void;
  /** Débat lancé : son fil est ouvert */
  onStarted: (runId: string) => void;
}

/** Monté le temps du choix : il part des deux premiers agents de la grille, comme Tk */
export function DebateDialog({ onClose, onStarted }: DebateDialogProps) {
  const t = useT();
  const builtin = useAgents((state) => state.builtin);
  const custom = useAgents((state) => state.custom);
  const agents = [...builtin, ...custom];
  const [agentA, setAgentA] = useState(agents[0]?.key ?? '');
  const [agentB, setAgentB] = useState(agents[1]?.key ?? agents[0]?.key ?? '');
  const [topic, setTopic] = useState('');
  const [rounds, setRounds] = useState('3');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const aId = useId();
  const bId = useId();
  const topicId = useId();
  const roundsId = useId();

  const submit = async () => {
    // Contrôles de Tk (_open_debate_dialog), dans son ordre
    if (!agentA || !agentB || agentA === agentB) {
      setError(t('agents.debate.differentAgents'));
      return;
    }
    if (!topic.trim()) {
      setError(t('agents.debate.topicRequired'));
      return;
    }
    const parsed = Number.parseInt(rounds, 10);
    const count = Math.max(1, Math.min(10, Number.isNaN(parsed) ? 3 : parsed));
    setBusy(true);
    setError('');
    try {
      const runId = await startDebate(agentA, agentB, topic.trim(), count);
      onStarted(runId);
      onClose();
    } catch (failure) {
      setError(errorText(failure));
      setBusy(false);
    }
  };

  const options = agents.map((agent) => (
    <option key={agent.key} value={agent.key}>
      {agent.name}
      {agent.desc ? ` · ${agent.desc}` : ''}
    </option>
  ));

  return (
    <Dialog
      open
      onOpenChange={(next) => {
        if (!next && !busy) onClose();
      }}
      title={t('agents.debate.title')}
      description={t('agents.debate.description')}
      width={520}
      dismissible={!busy}
      footer={
        <>
          <Button variant="secondary" disabled={busy} onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button variant="primary" disabled={busy} onClick={() => void submit()}>
            {t('agents.debate.start')}
          </Button>
        </>
      }
    >
      <form
        className="flex flex-col gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          void submit();
        }}
      >
        <label htmlFor={aId} className="text-sm font-semibold text-fg">
          {t('agents.debate.agentA')}
        </label>
        <select
          id={aId}
          value={agentA}
          disabled={busy}
          onChange={(event) => setAgentA(event.target.value)}
          className={fieldClass}
        >
          {options}
        </select>
        <label htmlFor={bId} className="mt-1 text-sm font-semibold text-fg">
          {t('agents.debate.agentB')}
        </label>
        <select
          id={bId}
          value={agentB}
          disabled={busy}
          onChange={(event) => setAgentB(event.target.value)}
          className={fieldClass}
        >
          {options}
        </select>
        <label htmlFor={topicId} className="mt-1 text-sm font-semibold text-fg">
          {t('agents.debate.topic')}
        </label>
        <textarea
          id={topicId}
          value={topic}
          disabled={busy}
          autoFocus
          rows={3}
          maxLength={100_000}
          placeholder={t('agents.debate.topicPlaceholder')}
          onChange={(event) => setTopic(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === 'Enter' && (event.ctrlKey || event.metaKey)) {
              event.preventDefault();
              void submit();
            }
          }}
          className="resize-none rounded-md border border-line bg-bg px-3 py-2 text-sm leading-relaxed text-fg outline-none placeholder:text-fg-3 focus:border-line-2"
        />
        <div className="mt-1 flex items-center gap-3">
          <label htmlFor={roundsId} className="text-sm font-semibold text-fg">
            {t('agents.debate.rounds')}
          </label>
          <input
            id={roundsId}
            type="number"
            min={1}
            max={10}
            value={rounds}
            disabled={busy}
            onChange={(event) => setRounds(event.target.value)}
            className="h-9 w-20 rounded-md border border-line bg-bg px-2.5 text-sm text-fg tabular-nums outline-none focus:border-line-2"
          />
        </div>
        <div className="min-h-5 text-sm text-error" aria-live="polite">
          {error}
        </div>
      </form>
    </Dialog>
  );
}
