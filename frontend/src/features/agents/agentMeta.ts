/*
 * Agents : icône, couleur, statuts.
 *
 * Les icônes des agents intégrés, des émojis dans Tk (🐍 🔍 📊 ✨ 🐛 📋 🛡 ⚡
 * 🧬), deviennent leurs équivalents lucide, teintés de la couleur de l'agent
 * (§8). Leurs couleurs passent par les jetons --agent-* de tokens.css ; un
 * agent personnalisé garde la couleur tirée à sa création.
 */

import {
  Bot,
  Bug,
  ChartColumn,
  ClipboardList,
  Code,
  Dna,
  Search,
  Shield,
  Sparkles,
  Zap,
  type LucideIcon,
} from 'lucide-react';

import type { MessageKey } from '../../i18n';
import type { NodeStatus, RunOrigin, RunStatus } from '../../lib/events';

const BUILTIN_ICONS: Record<string, LucideIcon> = {
  code: Code,
  web: Search,
  analyst: ChartColumn,
  creative: Sparkles,
  debug: Bug,
  planner: ClipboardList,
  security: Shield,
  optimizer: Zap,
  datascience: Dna,
};

/** Émojis des agents dans les fichiers de workflow (WorkflowCanvas.to_dict de Tk) */
const BUILTIN_EMOJIS: Record<string, string> = {
  code: '🐍',
  web: '🔍',
  analyst: '📊',
  creative: '✨',
  debug: '🐛',
  planner: '📋',
  security: '🛡',
  optimizer: '⚡',
  datascience: '🧬',
};

export function isBuiltin(agentType: string | null | undefined): boolean {
  return Boolean(agentType && agentType in BUILTIN_ICONS);
}

/** Icône d'un agent ; un agent personnalisé a le robot (🤖 dans la grille de Tk) */
export function agentIcon(agentType: string | null | undefined): LucideIcon {
  return (agentType && BUILTIN_ICONS[agentType]) || Bot;
}

/** Émoji d'un agent dans un fichier de workflow (🤖 pour un agent personnalisé, comme Tk) */
export function agentEmoji(agentType: string): string {
  return BUILTIN_EMOJIS[agentType] ?? '🤖';
}

/** Couleur d'affichage : jeton de tokens.css pour un agent intégré, la sienne sinon */
export function agentColor(agentType: string | null | undefined, fallback?: string | null): string {
  if (agentType && agentType in BUILTIN_ICONS) return `var(--agent-${agentType})`;
  return fallback || 'var(--accent)';
}

/** Teinte transparente d'une couleur (fond d'une icône, halo) */
export function tint(color: string, percent: number): string {
  return `color-mix(in srgb, ${color} ${percent}%, transparent)`;
}

/** Statuts d'un nœud (WorkflowCanvas.STATUS_META de Tk) ; libellés : clés du catalogue */
export const NODE_STATUS: Record<NodeStatus, { label: MessageKey; color: string }> = {
  idle: { label: 'agents.node.idle', color: 'var(--text-muted)' },
  running: { label: 'agents.node.running', color: 'var(--warning)' },
  done: { label: 'agents.node.done', color: 'var(--success)' },
  error: { label: 'agents.node.error', color: 'var(--error)' },
};

/** Agent en cours qui attend que le modèle ait fini de répondre à un autre (queuedBehind) */
export const QUEUED: { label: MessageKey; color: string } = {
  label: 'agents.queued',
  color: 'var(--text-muted)',
};

/** Origine d'un fil venu d'ailleurs que la page (D37) */
export const ORIGIN_LABEL: Record<Exclude<RunOrigin, 'desktop'>, MessageKey> = {
  mobile: 'agents.origin.mobile',
  scheduled: 'agents.origin.scheduled',
};

/** Statut affiché d'un fil ; partial : workflow terminé avec des agents en échec */
export type RunTone = RunStatus | 'partial';

/**
 * AgentRelayService finit un workflow par « ✅ Workflow terminé (50% succès) »
 * même si des agents ont échoué : c'est un succès partiel, montré en orange,
 * ni un succès ni une erreur. À 0 %, c'est un échec. Le taux est le nombre
 * suivi de « % » entre parenthèses (pleine chasse en chinois et en japonais) :
 * le texte est dans la langue du serveur.
 */
export function runTone(status: RunStatus, statusText: string): RunTone {
  if (status !== 'error' || !statusText.startsWith('✅')) return status;
  const rate = /[(（]\s*(\d+)\s*%/.exec(statusText);
  return rate && Number(rate[1]) > 0 ? 'partial' : 'error';
}

export const RUN_TONE: Record<RunTone, { label: MessageKey; color: string; chip: string }> = {
  running: {
    label: 'agents.node.running',
    color: 'var(--warning)',
    chip: 'bg-warning-soft text-warning',
  },
  done: {
    label: 'agents.node.done',
    color: 'var(--success)',
    chip: 'bg-success-soft text-success',
  },
  partial: {
    label: 'agents.run.partial',
    color: 'var(--warning)',
    chip: 'bg-warning-soft text-warning',
  },
  error: { label: 'agents.node.error', color: 'var(--error)', chip: 'bg-error-soft text-error' },
  interrupted: {
    label: 'agents.run.interrupted',
    color: 'var(--text-secondary)',
    chip: 'bg-active text-fg-2',
  },
};
