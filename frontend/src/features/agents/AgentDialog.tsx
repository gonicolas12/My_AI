/*
 * Créer ou modifier un agent personnalisé (custom_agents.py de Tk).
 *
 * Le modèle rédige son prompt système, sa température et sa description
 * courte : un changement de rôle le fait réécrire, un changement de nom seul
 * est immédiat. Pendant la rédaction, le dialogue attend (boutons grisés,
 * comme Tk) ; une erreur s'affiche sous les champs.
 */

import { LoaderCircle } from 'lucide-react';
import { useId, useState } from 'react';

import { Button } from '../../components/ui/Button';
import { Dialog } from '../../components/ui/Dialog';
import { useT } from '../../i18n';
import type { AgentInfo } from '../../lib/events';
import { createAgent, editAgent, errorText } from '../../stores/agents';

interface AgentDialogProps {
  /** Agent à modifier ; null : création */
  agent: AgentInfo | null;
  onClose: () => void;
}

/** Monté le temps de l'édition : ses champs partent de l'agent à modifier */
export function AgentDialog({ agent, onClose }: AgentDialogProps) {
  const t = useT();
  const [name, setName] = useState(agent?.name ?? '');
  const [role, setRole] = useState(agent?.full_desc ?? agent?.desc ?? '');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const nameId = useId();
  const roleId = useId();

  const submit = async () => {
    const cleanName = name.trim();
    const cleanRole = role.trim();
    // Contrôles de Tk (messagebox « Nom requis », « Rôle requis »)
    if (!cleanName) {
      setError(t('agents.dialog.nameRequired'));
      return;
    }
    if (!cleanRole) {
      setError(t('agents.dialog.roleRequired'));
      return;
    }
    if (agent && cleanName === agent.name && cleanRole === (agent.full_desc ?? agent.desc)) {
      onClose();
      return;
    }
    setBusy(true);
    setError('');
    try {
      if (agent) await editAgent(agent.key, cleanName, cleanRole);
      else await createAgent(cleanName, cleanRole);
      onClose();
    } catch (failure) {
      setError(errorText(failure));
      setBusy(false);
    }
  };

  const renaming = agent !== null && role.trim() === (agent.full_desc ?? agent.desc);
  return (
    <Dialog
      open
      onOpenChange={(next) => {
        if (!next && !busy) onClose();
      }}
      title={
        agent ? t('agents.dialog.editTitle', { name: agent.name }) : t('agents.dialog.createTitle')
      }
      description={
        agent ? t('agents.dialog.editDescription') : t('agents.dialog.createDescription')
      }
      width={500}
      dismissible={!busy}
      footer={
        <>
          <Button variant="secondary" disabled={busy} onClick={onClose}>
            {t('common.cancel')}
          </Button>
          <Button variant="primary" disabled={busy} onClick={() => void submit()}>
            {agent ? t('agents.dialog.save') : t('agents.dialog.create')}
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
        <label htmlFor={nameId} className="text-sm font-semibold text-fg">
          {t('agents.dialog.name')}
        </label>
        <input
          id={nameId}
          value={name}
          disabled={busy}
          autoFocus
          maxLength={200}
          placeholder={t('agents.dialog.namePlaceholder')}
          onChange={(event) => setName(event.target.value)}
          className="h-9 rounded-md border border-line bg-bg px-3 text-sm text-fg outline-none placeholder:text-fg-3 focus:border-line-2"
        />
        <label htmlFor={roleId} className="mt-1 text-sm font-semibold text-fg">
          {t('agents.dialog.role')}
        </label>
        <textarea
          id={roleId}
          value={role}
          disabled={busy}
          rows={4}
          maxLength={5000}
          placeholder={t('agents.dialog.rolePlaceholder')}
          onChange={(event) => setRole(event.target.value)}
          className="resize-none rounded-md border border-line bg-bg px-3 py-2 text-sm leading-relaxed text-fg outline-none placeholder:text-fg-3 focus:border-line-2"
        />
        <div className="min-h-5 text-sm" aria-live="polite">
          {busy ? (
            <span className="flex items-center gap-2 text-warning">
              <LoaderCircle size={14} className="spin" />
              {renaming ? t('agents.dialog.saving') : t('agents.dialog.generating')}
            </span>
          ) : error ? (
            <span className="text-error">{error}</span>
          ) : null}
        </div>
      </form>
    </Dialog>
  );
}
