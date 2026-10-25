/*
 * Nœud du canvas : un agent du workflow (_draw_node de WorkflowCanvas, Tk).
 *
 * Liseré et pastille à la couleur de l'agent, nom, statut de la dernière
 * exécution (en attente, en cours, attend son tour, terminé, erreur), port
 * d'entrée à gauche, de sortie à droite, ✕ pour le retirer.
 */

import { Handle, type NodeProps, Position } from '@xyflow/react';
import { X } from 'lucide-react';
import { createElement, memo } from 'react';

import { useT } from '../../../i18n';
import { cn } from '../../../lib/cn';
import { useAgents } from '../../../stores/agents';
import { agentColor, agentIcon, NODE_STATUS, QUEUED, tint } from '../agentMeta';
import { NODE_H, NODE_W } from './graph';
import { type AgentFlowNode, removeNode } from './workflowStore';

/** L'agent existe encore (un agent personnalisé a pu être supprimé depuis l'enregistrement) */
function useAgentKnown(agentType: string): boolean {
  return useAgents(
    (state) =>
      !state.loaded ||
      state.builtin.some((agent) => agent.key === agentType) ||
      state.custom.some((agent) => agent.key === agentType),
  );
}

export const AgentNode = memo(function AgentNode({ id, data, selected }: NodeProps<AgentFlowNode>) {
  const t = useT();
  const status = data.status ?? 'idle';
  const queued = status === 'running' && Boolean(data.queuedBehind);
  const meta = queued ? QUEUED : NODE_STATUS[status];
  const color = agentColor(data.agentType, data.color);
  const known = useAgentKnown(data.agentType);
  const running = status === 'running' && !queued;
  return (
    <div
      className={cn(
        'relative flex items-center gap-3 rounded-[14px] border bg-bg-3 pr-8 pl-4 shadow-md',
        'transition-[border-color,box-shadow] duration-150',
      )}
      style={{
        width: NODE_W,
        height: NODE_H,
        borderColor: running ? meta.color : selected ? color : 'var(--border)',
        boxShadow: running
          ? `0 0 0 3px ${tint(meta.color, 22)}`
          : selected
            ? `0 0 0 2px ${tint(color, 35)}`
            : undefined,
      }}
      title={t('canvas.node.title', {
        name: data.name,
        status: !known
          ? t('canvas.node.unknown')
          : queued
            ? t('canvas.node.queued', { label: t(meta.label), name: data.queuedBehind ?? '' })
            : t(meta.label),
      })}
    >
      <span
        aria-hidden
        className="absolute top-3 bottom-3 left-0 w-1 -translate-x-1/2 rounded-full"
        style={{ background: color }}
      />
      <span
        aria-hidden
        className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full text-white"
        style={{ background: color }}
      >
        {createElement(agentIcon(data.agentType), { size: 18 })}
      </span>
      <div className="min-w-0">
        <div className="truncate text-[15px] font-semibold text-fg">{data.name}</div>
        {known ? (
          <div className="flex items-center gap-1.5 text-xs text-fg-2">
            <span
              className={cn('h-2 w-2 rounded-full', (running || queued) && 'pulse-soft')}
              style={{ background: meta.color }}
            />
            {t(meta.label)}
          </div>
        ) : (
          <div className="text-xs text-error">{t('canvas.node.unknownTitle')}</div>
        )}
      </div>
      <button
        type="button"
        aria-label={t('canvas.node.remove', { name: data.name })}
        title={t('canvas.node.removeTitle')}
        onClick={() => removeNode(id)}
        className="nodrag nopan absolute top-1.5 right-1.5 rounded-xs p-1 text-fg-3 hover:bg-hover hover:text-fg"
      >
        <X size={13} />
      </button>
      <Handle
        type="target"
        position={Position.Left}
        className="agent-port"
        style={{ borderColor: color }}
      />
      <Handle
        type="source"
        position={Position.Right}
        className="agent-port"
        style={{ borderColor: color }}
      />
    </div>
  );
});
