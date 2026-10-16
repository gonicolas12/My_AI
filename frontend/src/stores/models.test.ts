import { beforeEach, describe, expect, it } from 'vitest';

import {
  applyModelDone,
  applyModelLog,
  applyModelProgress,
  beginModelJob,
  failModelJob,
  progressLabel,
  useModels,
} from './models';

beforeEach(() => {
  useModels.setState({ job: null });
});

describe('travail sur les modèles', () => {
  it('repart de zéro puis suit progression, journal et fin', () => {
    beginModelJob('pull', 'llava:7b');
    applyModelLog({ line: '📥 Téléchargement de llava:7b…' });
    applyModelProgress({ fraction: 0.42, status: 'pulling 2f5d…' });
    applyModelDone({
      action: 'pull',
      name: 'llava:7b',
      ok: true,
      message: '✅ llava:7b téléchargé',
    });

    const job = useModels.getState().job!;
    expect(job.log).toEqual(['📥 Téléchargement de llava:7b…']);
    expect(job.running).toBe(false);
    expect(job.ok).toBe(true);
    expect(progressLabel(job)).toBe('pulling 2f5d… — 42%');
  });

  it('ignore les événements sans travail suivi, et note un refus', () => {
    applyModelLog({ line: 'perdue' });
    expect(useModels.getState().job).toBeNull();

    beginModelJob('apply', 'qwen3.5:4b');
    failModelJob("Ollama n'est pas joignable.");
    expect(useModels.getState().job).toMatchObject({
      running: false,
      ok: false,
      message: "Ollama n'est pas joignable.",
    });
  });
});
