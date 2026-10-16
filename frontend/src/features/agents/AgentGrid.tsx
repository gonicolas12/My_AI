/*
 * Grille des agents (agent_selection.py, custom_agents.py de Tk) : les 9
 * agents intégrés puis les agents personnalisés, trois par ligne.
 *
 * Une carte se glisse sur le canvas, où elle devient un nœud ; un clic (ou
 * Entrée) l'y ajoute en cascade. Un agent personnalisé se modifie ou se
 * supprime depuis sa carte (boutons au survol).
 */

import { Pencil, X } from 'lucide-react';
import { createElement, useState } from 'react';

import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { IconButton } from '../../components/ui/Button';
import { cn } from '../../lib/cn';
import type { AgentInfo } from '../../lib/events';
import { deleteAgent, useAgents } from '../../stores/agents';
import { agentColor, agentIcon, tint } from './agentMeta';
import { AgentDialog } from './AgentDialog';
import { AGENT_MIME } from './canvas/WorkflowCanvas';
import { addAgentNode, removeAgentNodes } from './canvas/workflowStore';

/** Étiquette glissée sous le curseur, à la couleur de l'agent (comme Tk) */
function dragImage(agent: AgentInfo, color: string): HTMLElement {
  const label = document.createElement('div');
  label.textContent = agent.name;
  Object.assign(label.style, {
    position: 'fixed',
    top: '-100px',
    left: '-100px',
    padding: '6px 12px',
    borderRadius: '8px',
    background: color,
    color: 'white',
    font: '600 13px var(--font-ui)',
    whiteSpace: 'nowrap',
  });
  document.body.appendChild(label);
  setTimeout(() => label.remove(), 0);
  return label;
}

function AgentCard({
  agent,
  onEdit,
  onDelete,
}: {
  agent: AgentInfo;
  onEdit?: (() => void) | undefined;
  onDelete?: (() => void) | undefined;
}) {
  const color = agentColor(agent.key, agent.color);
  const add = () => addAgentNode(agent);
  return (
    <div
      role="button"
      tabIndex={0}
      draggable
      aria-label={`${agent.name} : ${agent.desc}. Ajouter au workflow`}
      title="Glissez sur le canvas, ou cliquez pour ajouter au workflow"
      onClick={add}
      onKeyDown={(event) => {
        if (event.target !== event.currentTarget) return;
        if (event.key === 'Enter' || event.key === ' ') {
          event.preventDefault();
          add();
        }
      }}
      onDragStart={(event) => {
        event.dataTransfer.setData(AGENT_MIME, agent.key);
        event.dataTransfer.effectAllowed = 'copy';
        event.dataTransfer.setDragImage(dragImage(agent, color), 12, 12);
      }}
      className={cn(
        'group relative flex cursor-grab items-center gap-3 rounded-lg border border-line/75 bg-bg-2 px-4 py-3',
        'transition-colors duration-150 select-none hover:border-[var(--card-color)] active:cursor-grabbing',
      )}
      style={{ '--card-color': color } as React.CSSProperties}
    >
      <span
        className="flex h-10 w-10 shrink-0 items-center justify-center rounded-md"
        style={{ background: tint(color, 15), color }}
      >
        {createElement(agentIcon(agent.custom ? null : agent.key), { size: 20 })}
      </span>
      <div className="min-w-0 flex-1">
        <div className="truncate text-[15px] font-semibold" style={{ color }}>
          {agent.name}
        </div>
        <div className="truncate text-sm text-fg-2" title={agent.full_desc || agent.desc}>
          {agent.desc}
        </div>
      </div>
      {agent.custom ? (
        <div className="flex items-center gap-0.5 opacity-0 transition-opacity duration-150 group-focus-within:opacity-100 group-hover:opacity-100">
          <IconButton
            size="sm"
            label={`Modifier ${agent.name}`}
            onClick={(event) => {
              event.stopPropagation();
              onEdit?.();
            }}
          >
            <Pencil size={14} />
          </IconButton>
          <IconButton
            size="sm"
            label={`Supprimer ${agent.name}`}
            onClick={(event) => {
              event.stopPropagation();
              onDelete?.();
            }}
            className="hover:text-error"
          >
            <X size={15} />
          </IconButton>
        </div>
      ) : null}
    </div>
  );
}

export function AgentGrid() {
  const builtin = useAgents((state) => state.builtin);
  const custom = useAgents((state) => state.custom);
  const [editing, setEditing] = useState<AgentInfo | null>(null);
  const [removing, setRemoving] = useState<AgentInfo | null>(null);
  return (
    <>
      <div className="grid grid-cols-3 gap-3" aria-label="Agents">
        {builtin.map((agent) => (
          <AgentCard key={agent.key} agent={agent} />
        ))}
        {custom.map((agent) => (
          <AgentCard
            key={agent.key}
            agent={agent}
            onEdit={() => setEditing(agent)}
            onDelete={() => setRemoving(agent)}
          />
        ))}
      </div>
      {editing ? <AgentDialog agent={editing} onClose={() => setEditing(null)} /> : null}
      <ConfirmDialog
        open={removing !== null}
        onOpenChange={(open) => {
          if (!open) setRemoving(null);
        }}
        title="Supprimer l'agent"
        message={`Voulez-vous vraiment supprimer l'agent '${removing?.name ?? ''}' ?`}
        confirmLabel="Supprimer"
        danger
        onConfirm={() => {
          const agent = removing;
          if (!agent) return;
          void deleteAgent(agent.key).then((deleted) => {
            // Ses nœuds quittent le canvas : ils ne pourraient plus s'exécuter
            if (deleted) removeAgentNodes(agent.key);
          });
        }}
      />
    </>
  );
}
