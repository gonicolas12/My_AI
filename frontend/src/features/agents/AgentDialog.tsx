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
import type { AgentInfo } from '../../lib/events';
import { createAgent, editAgent, errorText } from '../../stores/agents';

interface AgentDialogProps {
  /** Agent à modifier ; null : création */
  agent: AgentInfo | null;
  onClose: () => void;
}

/** Monté le temps de l'édition : ses champs partent de l'agent à modifier */
export function AgentDialog({ agent, onClose }: AgentDialogProps) {
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
      setError("Veuillez entrer un nom pour l'agent.");
      return;
    }
    if (!cleanRole) {
      setError("Veuillez décrire le rôle de l'agent.");
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
      title={agent ? `Modifier ${agent.name}` : 'Créer un agent personnalisé'}
      description={
        agent
          ? 'Un nouveau rôle fait réécrire son prompt système par le modèle ; un nouveau nom seul est immédiat.'
          : 'Le modèle rédige son prompt système, sa température et une description courte.'
      }
      width={500}
      dismissible={!busy}
      footer={
        <>
          <Button variant="secondary" disabled={busy} onClick={onClose}>
            Annuler
          </Button>
          <Button variant="primary" disabled={busy} onClick={() => void submit()}>
            {agent ? 'Sauvegarder' : 'Créer'}
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
          Nom de l&apos;agent
        </label>
        <input
          id={nameId}
          value={name}
          disabled={busy}
          autoFocus
          maxLength={200}
          placeholder="Ex : TranslatorAgent"
          onChange={(event) => setName(event.target.value)}
          className="h-9 rounded-md border border-line bg-bg px-3 text-sm text-fg outline-none placeholder:text-fg-3 focus:border-line-2"
        />
        <label htmlFor={roleId} className="mt-1 text-sm font-semibold text-fg">
          Rôle / Description
        </label>
        <textarea
          id={roleId}
          value={role}
          disabled={busy}
          rows={4}
          maxLength={5000}
          placeholder="Ex : Expert en traduction multilingue avec adaptation culturelle"
          onChange={(event) => setRole(event.target.value)}
          className="resize-none rounded-md border border-line bg-bg px-3 py-2 text-sm leading-relaxed text-fg outline-none placeholder:text-fg-3 focus:border-line-2"
        />
        <div className="min-h-5 text-sm" aria-live="polite">
          {busy ? (
            <span className="flex items-center gap-2 text-warning">
              <LoaderCircle size={14} className="spin" />
              {renaming ? 'Enregistrement…' : 'Génération du system prompt en cours…'}
            </span>
          ) : error ? (
            <span className="text-error">{error}</span>
          ) : null}
        </div>
      </form>
    </Dialog>
  );
}
