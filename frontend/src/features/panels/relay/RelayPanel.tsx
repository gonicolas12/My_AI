/*
 * My_AI Relay (_show_relay_info_popup de Tk) : accès depuis le téléphone.
 * L'ouverture démarre le Relay s'il ne tourne pas (_toggle_relay, qui ne
 * l'arrête jamais). Le panneau montre l'état des tunnels (vérifiés depuis ce
 * PC : tunnels.ts), le QR code de la page de routage (tunnels joignables,
 * dessiné une fois la liste stable), l'adresse à copier, le jeton et les
 * appareils connectés ; « Arrêter le Relay » l'arrête et ferme le panneau.
 */

import {
  Check,
  CircleCheck,
  Copy,
  Hourglass,
  LoaderCircle,
  Power,
  Puzzle,
  Radio,
  Smartphone,
  TriangleAlert,
} from 'lucide-react';
import { type ReactNode, useEffect, useState } from 'react';

import { Button } from '../../../components/ui/Button';
import { api } from '../../../lib/api';
import type { RelayStatus } from '../../../lib/events';
import { notify, useApp } from '../../../stores/app';
import { closePanel } from '../../../stores/panels';
import { PanelDialog } from '../PanelDialog';
import { tunnelView } from './tunnels';

/**
 * Liste des tunnels stable pendant ce délai avant de dessiner le QR code (Tk :
 * un cycle de 2 s) : chaque tunnel qui arrive change le code, et un téléphone
 * qui scanne pendant ce temps lirait un code périmé.
 */
const QR_SETTLE_MS = 2000;
const QR_SIZE = 280;

/** Un seul démarrage à la fois (double effet du StrictMode, Ctrl+R répété) */
let starting: Promise<RelayStatus> | null = null;

function startRelay(): Promise<RelayStatus> {
  starting ??= api
    .startRelay()
    .then((status) => {
      useApp.setState({ relay: status });
      return status;
    })
    .finally(() => {
      starting = null;
    });
  return starting;
}

/** Adresse affichée : coupée comme dans Tk */
const shortUrl = (url: string) => (url.length < 60 ? url : `${url.slice(0, 57)}...`);

/** Modules foncés en couleur d'accent sur le fond, comme le canevas de Tk */
function QrCode({ rows }: { rows: string[] }) {
  const count = rows.length;
  const cell = Math.max(1, Math.floor(QR_SIZE / count));
  // Un tracé par suite de modules foncés sur une ligne
  let path = '';
  rows.forEach((row, y) => {
    for (let x = 0; x < row.length;) {
      if (row[x] !== '1') {
        x += 1;
        continue;
      }
      let end = x;
      while (row[end] === '1') end += 1;
      path += `M${x} ${y}h${end - x}v1h${x - end}z`;
      x = end;
    }
  });
  return (
    <svg
      width={cell * count}
      height={cell * count}
      viewBox={`0 0 ${count} ${count}`}
      shapeRendering="crispEdges"
      role="img"
      aria-label="QR code du Relay"
    >
      <rect width={count} height={count} style={{ fill: 'var(--bg-primary)' }} />
      <path d={path} style={{ fill: 'var(--accent)' }} />
    </svg>
  );
}

/** Libellé passager d'un bouton de copie */
function useFlash(): [string, (label: string, ms: number) => void] {
  const [label, setLabel] = useState('');
  const flash = (text: string, ms: number) => {
    setLabel(text);
    setTimeout(() => setLabel((current) => (current === text ? '' : current)), ms);
  };
  return [label, flash];
}

function Running({ relay }: { relay: RelayStatus }) {
  const view = tunnelView(relay);
  const { ready } = view;
  const target = ready ? relay.url : null;
  const current = (ready ? relay.url : relay.local_url) ?? '';
  const [qr, setQr] = useState<{ url: string; rows: string[] } | null>(null);
  const [copyLabel, flashCopy] = useFlash();
  const [vscodeLabel, flashVscode] = useFlash();

  useEffect(() => {
    if (!target || qr?.url === target) return;
    let alive = true;
    const timer = setTimeout(() => {
      api.relayQr().then(
        (data) => {
          if (alive) setQr(data);
        },
        () => undefined,
      );
    }, QR_SETTLE_MS);
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [target, qr?.url]);

  const copy = (text: string, done: () => void) => {
    navigator.clipboard.writeText(text).then(done, () => notify('error', 'Copie impossible.'));
  };

  const copyVscode = () => {
    // La même adresse que le QR code : l'extension lit tunnels, jeton et clé dans le fragment
    if (!ready || !relay.url) {
      flashVscode('Tunnel non prêt', 2000);
      return;
    }
    copy(relay.url, () => flashVscode('Copié — collez dans VS Code', 2500));
  };

  const statusIcon = view.busy ? (
    <LoaderCircle size={15} className="spin shrink-0" />
  ) : view.tone === 'success' ? (
    <CircleCheck size={15} className="shrink-0" />
  ) : (
    <TriangleAlert size={15} className="shrink-0" />
  );

  return (
    <div className="flex flex-col items-center gap-4">
      <div className="flex flex-col items-center gap-1">
        <p
          className={`flex items-center gap-2 text-center text-sm ${
            view.tone === 'success' ? 'text-success' : 'text-warning'
          }`}
          role="status"
        >
          {statusIcon} {view.status}
        </p>
        {view.others.length ? (
          <ul className="flex flex-wrap justify-center gap-x-3 text-xs text-fg-3">
            {view.others.map((tunnel) => (
              <li key={tunnel.name}>
                {tunnel.name} : {tunnel.label}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
      <div
        className="flex items-center justify-center rounded-lg border border-line bg-bg"
        style={{ width: QR_SIZE + 24, height: QR_SIZE + 24 }}
      >
        {target && qr ? (
          <QrCode rows={qr.rows} />
        ) : (
          <p className="text-center text-sm text-fg-3">
            En attente
            <br />
            du tunnel…
          </p>
        )}
      </div>
      <div className="flex w-full items-center gap-2 rounded-md border border-line bg-bg py-1.5 pr-1.5 pl-3">
        <code className="min-w-0 flex-1 truncate font-mono text-xs text-fg" title={current}>
          {shortUrl(current)}
        </code>
        <Button
          size="sm"
          variant="primary"
          onClick={() => copy(current, () => flashCopy('Copié !', 2000))}
          disabled={!current}
        >
          {copyLabel ? <Check size={14} /> : <Copy size={14} />}
          {copyLabel || 'Copier'}
        </Button>
      </div>
      <Button className="w-full" onClick={copyVscode}>
        {vscodeLabel === 'Tunnel non prêt' ? (
          <Hourglass size={15} />
        ) : vscodeLabel ? (
          <Check size={15} className="text-success" />
        ) : (
          <Puzzle size={15} />
        )}
        {vscodeLabel || 'Copier pour l’extension VS Code'}
      </Button>
      {relay.token ? (
        <p className="font-mono text-xs text-fg-3 select-text">Token : {relay.token}</p>
      ) : null}
      <p className="flex items-center gap-2 text-sm text-fg-2">
        <Smartphone size={15} /> {relay.clients} appareil(s) connecté(s)
      </p>
    </div>
  );
}

const Centered = ({ children }: { children: ReactNode }) => (
  <div className="flex flex-col items-center gap-4 py-20 text-center text-sm text-fg-2">
    {children}
  </div>
);

export default function RelayPanel() {
  const relay = useApp((state) => state.relay);
  const [attempt, setAttempt] = useState<'starting' | 'failed' | 'done'>(() =>
    useApp.getState().relay?.running ? 'done' : 'starting',
  );

  // Ouverture : démarrage si le Relay ne tourne pas
  useEffect(() => {
    if (useApp.getState().relay?.running) return;
    let alive = true;
    startRelay().then(
      (status) => {
        if (alive) setAttempt(status.running ? 'done' : 'failed');
      },
      () => {
        if (alive) setAttempt('failed');
      },
    );
    return () => {
      alive = false;
    };
  }, []);

  const start = () => {
    setAttempt('starting');
    startRelay().then(
      (status) => setAttempt(status.running ? 'done' : 'failed'),
      () => setAttempt('failed'),
    );
  };

  const stop = () => {
    api.stopRelay().then(
      (status) => useApp.setState({ relay: status }),
      () => undefined,
    );
    closePanel();
  };

  let body: ReactNode;
  if (relay?.running) {
    body = <Running relay={relay} />;
  } else if (attempt === 'starting') {
    body = (
      <Centered>
        <LoaderCircle size={22} className="spin text-accent" />
        Démarrage du Relay…
      </Centered>
    );
  } else {
    body = (
      <Centered>
        {attempt === 'failed' ? 'Impossible de démarrer My_AI Relay.' : 'Le Relay est arrêté.'}
        <Button variant="primary" onClick={start}>
          <Radio size={15} /> Démarrer le Relay
        </Button>
      </Centered>
    );
  }

  return (
    <PanelDialog
      open
      onOpenChange={(open) => {
        if (!open) closePanel();
      }}
      icon={Radio}
      title="My_AI Relay"
      description="Scannez le QR code ou copiez l'URL sur votre téléphone"
      width={520}
      footer={
        relay?.running ? (
          <Button onClick={stop}>
            <Power size={15} /> Arrêter le Relay
          </Button>
        ) : null
      }
    >
      {body}
    </PanelDialog>
  );
}
