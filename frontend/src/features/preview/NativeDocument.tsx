/*
 * Document Word, Excel ou PowerPoint dans la visionneuse de Windows
 * (native_viewer.py) : la page réserve sa place dans le volet, la visionneuse
 * s'y charge masquée puis s'y pose, suit ses déplacements et se masque sous les
 * couches de la page (nativeLayer.ts). En échec, le volet repasse à l'aperçu
 * HTML (onFailed), comme Tk.
 *
 * Un aperçu ouvert par-dessus (fenêtre d'une pièce jointe, panneau Mémoire)
 * prend la visionneuse ; celui-ci la retrouve à sa fermeture (claimNative).
 */

import { LoaderCircle } from 'lucide-react';
import { useEffect, useRef, useState } from 'react';

import { useT } from '../../i18n';
import type { PreviewView } from '../../lib/api';
import { shell } from '../../lib/shell';
import {
  claimNative,
  coversNative,
  deviceRect,
  type NativeHandle,
  nativeAppLabel,
} from './nativeLayer';

/** Contrôle régulier de la place, en plus des changements de la page (écran, échelle) */
const CHECK_MS = 500;

interface NativeDocumentProps {
  view: PreviewView;
  /** Masquée quoi qu'il arrive (volet en cours de redimensionnement ou d'ouverture) */
  hidden: boolean;
  onFailed: () => void;
}

export function NativeDocument({ view, hidden, onFailed }: NativeDocumentProps) {
  const slotRef = useRef<HTMLDivElement>(null);
  const failed = useRef(onFailed);
  const handle = useRef<NativeHandle | null>(null);
  const [ready, setReady] = useState(false);
  // Visionneuse à cet aperçu : un autre ouvert par-dessus la lui prend un temps
  const [active, setActive] = useState(true);

  useEffect(() => {
    failed.current = onFailed;
  }, [onFailed]);

  useEffect(() => {
    const claim = claimNative({
      resume: () => setActive(true),
      suspend: () => {
        setActive(false);
        setReady(false);
      },
    });
    handle.current = claim;
    return () => {
      handle.current = null;
      claim.release();
    };
  }, []);

  // Chargement, visionneuse masquée ; autre aperçu ou volet fermé : déchargée
  useEffect(() => {
    const slot = slotRef.current;
    if (!slot || !active) return undefined;
    let alive = true;
    void shell.nativePreview.show(view.id, deviceRect(slot.getBoundingClientRect())).then((ok) => {
      if (!alive) return;
      if (ok) setReady(true);
      else failed.current();
    });
    return () => {
      alive = false;
      // Cédée à un autre aperçu : c'est lui qui s'en sert désormais
      if (handle.current?.owns()) shell.nativePreview.close();
    };
  }, [view.id, active]);

  // Prête : posée sur sa place, recalée et masquée selon la page
  useEffect(() => {
    const slot = slotRef.current;
    if (!slot || !ready || !active) return undefined;
    let frame = 0;
    let last = '';
    const update = () => {
      frame = 0;
      const box = slot.getBoundingClientRect();
      const rect = deviceRect(box);
      const visible = !hidden && !coversNative(box, document, slot);
      const key = `${rect.x},${rect.y},${rect.width},${rect.height},${String(visible)}`;
      if (key === last) return;
      last = key;
      shell.nativePreview.place(rect, visible);
    };
    const schedule = () => {
      frame ||= requestAnimationFrame(update);
    };
    const mutations = new MutationObserver(schedule);
    mutations.observe(document.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['style', 'class', 'data-state', 'aria-hidden'],
    });
    const sizes = new ResizeObserver(schedule);
    sizes.observe(slot);
    window.addEventListener('resize', schedule);
    // Fin d'une entrée animée (toast, menu, volet) : sa place définitive, sans attendre le contrôle
    document.addEventListener('animationend', schedule, true);
    document.addEventListener('transitionend', schedule, true);
    const timer = window.setInterval(schedule, CHECK_MS);
    update();
    return () => {
      mutations.disconnect();
      sizes.disconnect();
      window.removeEventListener('resize', schedule);
      document.removeEventListener('animationend', schedule, true);
      document.removeEventListener('transitionend', schedule, true);
      window.clearInterval(timer);
      cancelAnimationFrame(frame);
    };
  }, [ready, hidden, active]);

  const label = nativeAppLabel(view.path ?? view.title);
  const t = useT();
  return (
    <div ref={slotRef} className="h-full w-full" data-native-preview={ready ? 'ready' : 'loading'}>
      {ready ? null : (
        <div className="flex h-full items-center justify-center gap-2 text-sm text-fg-2">
          <LoaderCircle size={16} className="spin text-accent" />
          {label ? t('preview.openingApp', { app: label }) : t('preview.opening')}
        </div>
      )}
    </div>
  );
}
