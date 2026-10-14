/*
 * Contenu d'un fil : une ligne par agent, dans l'ordre du plan d'exécution
 * (étapes, en parallèle ou non, puis agents isolés), y compris les agents qui
 * n'ont pas encore commencé, ou que l'arrêt a empêchés.
 */

import type { RunSection, RunView, SectionId } from '../../../lib/events';

export interface ThreadItem {
  key: string;
  /** Sortie de l'agent ; null tant qu'il n'a pas commencé */
  section: RunSection | null;
  title: string;
  agentType: string | null;
  color: string;
  /** « Étape 2/3 · parallèle », « Agent isolé », ou rien pour un agent seul */
  step: string;
  /** Agent sans sortie : il attend son tour, ou ne s'exécutera pas (fil terminé) */
  pending: 'waiting' | 'skipped' | null;
}

function same(a: SectionId, b: SectionId): boolean {
  return String(a) === String(b);
}

export function threadItems(run: RunView): ThreadItem[] {
  const items: ThreadItem[] = [];
  const used = new Set<string>();
  const ended = run.status !== 'running';

  const add = (id: SectionId, step: string) => {
    const section = run.sections.find((item) => same(item.id, id)) ?? null;
    const node = run.nodes.find((item) => same(item.id, id));
    used.add(String(id));
    items.push({
      key: String(id),
      section,
      title: section?.title || node?.name || String(id),
      agentType: section?.agent_type ?? node?.agent_type ?? null,
      color: section?.color || node?.color || '',
      step,
      pending: section ? null : ended ? 'skipped' : 'waiting',
    });
  };

  if (run.kind !== 'debate') {
    const steps = run.plan.steps;
    const single = run.kind === 'agent' || run.plan.mode === 'single';
    steps.forEach((step, index) => {
      let label = `Étape ${index + 1}/${steps.length}${step.length > 1 ? ' · parallèle' : ''}`;
      if (single) label = '';
      else if (steps.length === 1) label = 'En parallèle';
      for (const id of step) add(id, label);
    });
    for (const id of run.plan.isolated) add(id, 'Agent isolé');
  }
  // Sections hors du plan (tours d'un débat…), dans leur ordre d'arrivée
  for (const section of run.sections) {
    if (used.has(String(section.id))) continue;
    items.push({
      key: String(section.id),
      section,
      title: section.title,
      agentType: section.agent_type,
      color: section.color,
      step: '',
      pending: null,
    });
  }
  return items;
}

/** Plan en une ligne : « Étape 1 : A · Étape 2, en parallèle : B, C · Agents isolés : D » */
export function planSummary(run: RunView): string {
  if (run.kind !== 'workflow') return '';
  const name = (id: SectionId) => run.nodes.find((node) => same(node.id, id))?.name ?? String(id);
  const steps = run.plan.steps;
  const parts = steps.map((step, index) => {
    const names = step.map(name).join(', ');
    if (steps.length === 1) return `En parallèle : ${names}`;
    return step.length > 1
      ? `Étape ${index + 1}, en parallèle : ${names}`
      : `Étape ${index + 1} : ${names}`;
  });
  if (run.plan.isolated.length) {
    parts.push(
      `Agent${run.plan.isolated.length > 1 ? 's' : ''} isolé${run.plan.isolated.length > 1 ? 's' : ''} : ${run.plan.isolated.map(name).join(', ')}`,
    );
  }
  return parts.join(' · ');
}
