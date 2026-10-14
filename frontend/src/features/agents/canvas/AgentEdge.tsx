/*
 * Lien du canvas : courbe de Bézier horizontale, flèche au bout, couleur du
 * nœud source (_redraw_connections de Tk). Il s'anime tant que l'agent qu'il
 * alimente travaille.
 */

import { BaseEdge, type EdgeProps, getBezierPath } from '@xyflow/react';
import { memo } from 'react';

import type { AgentFlowEdge } from './workflowStore';

export const AgentEdge = memo(function AgentEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
}: EdgeProps<AgentFlowEdge>) {
  const [path] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    // La flèche s'arrête au bord du port d'entrée
    targetX: targetX - 6,
    targetY,
    targetPosition,
  });
  // Couleur du nœud source, posée à l'affichage (jeton d'un agent intégré)
  const color = data?.color ?? 'var(--border-light)';
  const marker = `agent-arrow-${id}`;
  return (
    <>
      <defs>
        <marker
          id={marker}
          viewBox="0 0 10 10"
          refX="8.5"
          refY="5"
          markerWidth="11"
          markerHeight="11"
          markerUnits="userSpaceOnUse"
          orient="auto-start-reverse"
        >
          <path d="M 0 0 L 10 5 L 0 10 z" style={{ fill: color }} />
        </marker>
      </defs>
      <BaseEdge
        id={id}
        path={path}
        markerEnd={`url(#${marker})`}
        interactionWidth={18}
        className={data?.running ? 'agent-edge-running' : undefined}
        style={{ stroke: color, strokeWidth: selected ? 3.5 : 2.5 }}
      />
    </>
  );
});
