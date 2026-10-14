/*
 * Hôte des panneaux : le panneau ouvert, chargé à la première ouverture
 * (morceaux séparés du build, hors du premier affichage).
 */

import { lazy, Suspense } from 'react';

import { usePanels } from '../../stores/panels';

const SettingsPanel = lazy(() => import('./settings/SettingsPanel'));
const HelpPanel = lazy(() => import('./help/HelpPanel'));

export function Panels() {
  const open = usePanels((state) => state.open);
  return (
    <Suspense fallback={null}>
      {open === 'settings' ? <SettingsPanel /> : null}
      {open === 'help' ? <HelpPanel /> : null}
    </Suspense>
  );
}
