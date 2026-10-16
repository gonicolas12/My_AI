/*
 * Canvas du workflow (WorkflowCanvas de Tk, avec React Flow) : les agents
 * glissés depuis la grille y deviennent des nœuds, reliés de port à port.
 *
 * Gestes de Tk : molette = zoom (0,3 à 3), clic milieu ou droit + glisser =
 * déplacement de la vue, glisser dans le vide = rectangle de sélection,
 * Maj+clic = sélection multiple, Suppr = retirer la sélection, clic droit sur
 * un lien = le supprimer, grille avec aimantation, minimap en bas à droite.
 * Pendant une exécution, chaque nœud montre son statut et les liens vers un
 * agent en cours s'animent ; un agent qui attend son tour auprès du modèle
 * (queuedBehind) le dit, et son lien reste immobile.
 */

import '@xyflow/react/dist/style.css';
import './canvas.css';

import {
  Background,
  BackgroundVariant,
  type ConnectionLineComponentProps,
  type EdgeTypes,
  getBezierPath,
  MiniMap,
  type NodeTypes,
  Panel,
  ReactFlow,
  ReactFlowProvider,
  SelectionMode,
  useReactFlow,
} from '@xyflow/react';
import {
  FileDown,
  FolderOpen,
  Grid3x3,
  Locate,
  Save,
  Workflow,
  ZoomIn,
  ZoomOut,
} from 'lucide-react';
import { useMemo, useRef, useState } from 'react';
import { useShallow } from 'zustand/react/shallow';

import { Button, IconButton } from '../../../components/ui/Button';
import { cn } from '../../../lib/cn';
import { useAgents } from '../../../stores/agents';
import { agentColor } from '../agentMeta';
import { queuedBehind } from '../runs/threadItems';
import {
  exportWorkflowFile,
  loadWorkflowBlob,
  loadWorkflowFile,
  saveWorkflowFile,
} from '../workflowActions';
import { AgentEdge } from './AgentEdge';
import { AgentNode } from './AgentNode';
import { GRID, MAX_ZOOM, MIN_ZOOM, NODE_H, NODE_W } from './graph';
import {
  type AgentFlowEdge,
  type AgentFlowNode,
  addAgentNode,
  connect,
  isValidLink,
  onEdgesChange,
  onNodesChange,
  removeEdge,
  setViewport,
  toggleGrid,
  useWorkflow,
} from './workflowStore';

/** Type des données glissées depuis une carte de la grille */
export const AGENT_MIME = 'application/x-myai-agent';

const NODE_TYPES: NodeTypes = { agent: AgentNode };
const EDGE_TYPES: EdgeTypes = { agent: AgentEdge };

/** Hauteur du canvas (380 px dans Tk) */
const CANVAS_HEIGHT = 380;

/** Lien en cours de tracé : pointillés à la couleur du nœud source */
function ConnectionLine({
  fromX,
  fromY,
  toX,
  toY,
  fromPosition,
  toPosition,
  fromNode,
}: ConnectionLineComponentProps<AgentFlowNode>) {
  const [path] = getBezierPath({
    sourceX: fromX,
    sourceY: fromY,
    sourcePosition: fromPosition,
    targetX: toX,
    targetY: toY,
    targetPosition: toPosition,
  });
  const color = agentColor(fromNode.data.agentType, fromNode.data.color);
  return (
    <path d={path} fill="none" className="react-flow__connection-path" style={{ stroke: color }} />
  );
}

function CanvasToolbar() {
  const flow = useReactFlow<AgentFlowNode, AgentFlowEdge>();
  const grid = useWorkflow((state) => state.grid);
  return (
    <div className="flex items-center gap-0.5 rounded-md border border-line bg-bg/90 p-0.5 shadow-sm">
      <IconButton size="sm" label="Zoom avant" onClick={() => void flow.zoomIn({ duration: 150 })}>
        <ZoomIn size={15} />
      </IconButton>
      <IconButton
        size="sm"
        label="Zoom arrière"
        onClick={() => void flow.zoomOut({ duration: 150 })}
      >
        <ZoomOut size={15} />
      </IconButton>
      <IconButton
        size="sm"
        label="Réinitialiser la vue"
        onClick={() => void flow.setViewport({ x: 0, y: 0, zoom: 1 }, { duration: 200 })}
      >
        <Locate size={15} />
      </IconButton>
      <IconButton
        size="sm"
        label={grid ? 'Masquer la grille' : 'Afficher la grille'}
        active={grid}
        onClick={toggleGrid}
      >
        <Grid3x3 size={15} />
      </IconButton>
    </div>
  );
}

function Flow() {
  const { nodes, edges, viewport, grid, runId } = useWorkflow(
    useShallow((state) => ({
      nodes: state.nodes,
      edges: state.edges,
      viewport: state.viewport,
      grid: state.grid,
      runId: state.runId,
    })),
  );
  const nodeStatus = useAgents((state) => (runId ? state.details[runId]?.node_status : undefined));
  // Relu à chaque fragment écrit, mais le même contenu ne redessine rien
  const queued = useAgents(
    useShallow((state) => queuedBehind(runId ? state.details[runId] : undefined)),
  );
  const flow = useReactFlow<AgentFlowNode, AgentFlowEdge>();
  const [over, setOver] = useState(false);

  // Statut de la dernière exécution lancée d'ici, posé sur chaque nœud
  const shownNodes = useMemo(
    () =>
      nodes.map((node) => {
        const status = nodeStatus?.[node.id] ?? 'idle';
        const behind = queued[node.id];
        if (node.data.status === status && node.data.queuedBehind === behind) return node;
        return { ...node, data: { ...node.data, status, queuedBehind: behind } };
      }),
    [nodes, nodeStatus, queued],
  );
  const shownEdges = useMemo(
    () =>
      edges.map((edge) => {
        const running = nodeStatus?.[edge.target] === 'running' && !queued[edge.target];
        if (Boolean(edge.data?.running) === running) return edge;
        return { ...edge, data: { color: edge.data?.color ?? 'var(--border-light)', running } };
      }),
    [edges, nodeStatus, queued],
  );

  const isAgentDrag = (event: React.DragEvent) =>
    Array.from(event.dataTransfer.types).includes(AGENT_MIME);

  return (
    <div
      className={cn(
        'relative transition-shadow duration-150',
        over && 'shadow-[inset_0_0_0_2px_var(--accent)]',
      )}
      style={{ height: CANVAS_HEIGHT }}
      onDragOver={(event) => {
        if (!isAgentDrag(event)) return;
        event.preventDefault();
        event.dataTransfer.dropEffect = 'copy';
        setOver(true);
      }}
      onDragLeave={(event) => {
        if (event.currentTarget.contains(event.relatedTarget as globalThis.Node | null)) return;
        setOver(false);
      }}
      onDrop={(event) => {
        if (!isAgentDrag(event)) return;
        event.preventDefault();
        setOver(false);
        const key = event.dataTransfer.getData(AGENT_MIME);
        const { builtin, custom } = useAgents.getState();
        const agent = [...builtin, ...custom].find((item) => item.key === key);
        if (!agent) return;
        // Nœud centré sur le curseur (drop_agent de Tk)
        const point = flow.screenToFlowPosition({ x: event.clientX, y: event.clientY });
        addAgentNode(agent, { x: point.x - NODE_W / 2, y: point.y - NODE_H / 2 });
      }}
      // Clic droit : déplacement de la vue ou suppression d'un lien, jamais le menu du navigateur
      onContextMenu={(event) => event.preventDefault()}
    >
      <ReactFlow<AgentFlowNode, AgentFlowEdge>
        className="agents-flow"
        aria-label="Canvas du workflow"
        nodes={shownNodes}
        edges={shownEdges}
        nodeTypes={NODE_TYPES}
        edgeTypes={EDGE_TYPES}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={(connection) => connect(connection.source, connection.target)}
        isValidConnection={(connection) => isValidLink(connection.source, connection.target)}
        onEdgeContextMenu={(event, edge) => {
          event.preventDefault();
          removeEdge(edge.id);
        }}
        connectionLineComponent={ConnectionLine}
        connectionRadius={26}
        defaultViewport={viewport}
        onMoveEnd={(_event, next) => setViewport(next)}
        minZoom={MIN_ZOOM}
        maxZoom={MAX_ZOOM}
        snapToGrid
        snapGrid={[GRID, GRID]}
        panOnDrag={[1, 2]}
        selectionOnDrag
        selectionMode={SelectionMode.Partial}
        selectionKeyCode={null}
        multiSelectionKeyCode="Shift"
        deleteKeyCode={['Delete', 'Backspace']}
        zoomOnDoubleClick={false}
        colorMode="dark"
        proOptions={{ hideAttribution: true }}
      >
        {grid ? (
          <Background
            id="grille"
            variant={BackgroundVariant.Dots}
            gap={GRID}
            size={2.4}
            color="var(--canvas-dot)"
          />
        ) : null}
        <MiniMap<AgentFlowNode>
          position="bottom-right"
          pannable
          zoomable
          ariaLabel="Minimap du workflow"
          nodeColor={(node) => agentColor(node.data.agentType, node.data.color)}
          nodeBorderRadius={4}
          style={{ width: 160, height: 100 }}
        />
        <Panel position="top-left">
          <CanvasToolbar />
        </Panel>
      </ReactFlow>
      {nodes.length ? null : (
        <p className="pointer-events-none absolute inset-x-0 top-1/2 -translate-y-1/2 text-center text-sm text-fg-3">
          Glissez un agent depuis la grille, ou cliquez sur sa carte
        </p>
      )}
    </div>
  );
}

/** Enregistrer, Charger, Exporter (workflow.py de Tk) */
function FileActions() {
  const input = useRef<HTMLInputElement>(null);
  return (
    <div className="ml-auto flex items-center gap-1">
      <Button variant="ghost" size="sm" onClick={() => void saveWorkflowFile()}>
        <Save size={15} />
        Enregistrer
      </Button>
      <Button
        variant="ghost"
        size="sm"
        onClick={() =>
          void loadWorkflowFile().then((done) => {
            if (!done) input.current?.click();
          })
        }
      >
        <FolderOpen size={15} />
        Charger
      </Button>
      <Button variant="ghost" size="sm" onClick={() => void exportWorkflowFile()}>
        <FileDown size={15} />
        Exporter
      </Button>
      <input
        ref={input}
        type="file"
        accept=".json,application/json"
        hidden
        onChange={(event) => {
          const file = event.target.files?.[0];
          event.target.value = '';
          if (file) void loadWorkflowBlob(file);
        }}
      />
    </div>
  );
}

export function WorkflowCanvas() {
  return (
    <section
      aria-label="Workflow visuel"
      className="overflow-hidden rounded-xl border border-line bg-bg-2"
    >
      <div className="flex h-11 items-center gap-2 border-b border-line/70 px-4">
        <Workflow size={15} className="text-fg-2" />
        <h2 className="text-sm font-normal text-fg-2">
          Workflow visuel — glissez des agents, reliez les ports
        </h2>
        <FileActions />
      </div>
      <ReactFlowProvider>
        <Flow />
      </ReactFlowProvider>
    </section>
  );
}
