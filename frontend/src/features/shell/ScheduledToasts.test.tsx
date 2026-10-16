import { act, fireEvent, render, screen } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import type { SchedulerResult } from '../../lib/events';
import { showScheduledResult, useApp } from '../../stores/app';
import { ScheduledToasts } from './ScheduledToasts';

const actions = vi.hoisted(() => ({ openFile: vi.fn(() => Promise.resolve()) }));
vi.mock('../../lib/actions', () => actions);

const RESULT: SchedulerResult = {
  task_id: 't1',
  name: 'Veille technologique',
  status: 'success',
  status_text: 'Terminée',
  summary: 'Trois articles retenus.',
  output_file: 'C:/My_AI/outputs/scheduled/veille.md',
  finished_at: '2026-10-13T08:00:00',
  os_toast_shown: false,
};

beforeEach(() => {
  vi.clearAllMocks();
  useApp.setState({ scheduledToasts: [], lastScheduled: null });
});

afterEach(() => {
  vi.useRealTimers();
});

describe('fin de tâche planifiée', () => {
  it("s'affiche dans l'appli et ouvre son rapport au clic", () => {
    render(<ScheduledToasts />);
    act(() => showScheduledResult(RESULT));
    expect(screen.getByText('Trois articles retenus.')).toBeTruthy();
    fireEvent.click(screen.getByText('Veille technologique'));
    expect(actions.openFile).toHaveBeenCalledWith('C:/My_AI/outputs/scheduled/veille.md');
    expect(screen.queryByText('Veille technologique')).toBeNull();
  });

  it('disparaît seul après 6 s', () => {
    vi.useFakeTimers();
    render(<ScheduledToasts />);
    act(() => showScheduledResult(RESULT));
    act(() => {
      vi.advanceTimersByTime(5900);
    });
    expect(screen.getByText('Veille technologique')).toBeTruthy();
    act(() => {
      vi.advanceTimersByTime(200);
    });
    expect(screen.queryByText('Veille technologique')).toBeNull();
  });

  it('ne double pas la notification déjà montrée par le système', () => {
    showScheduledResult({ ...RESULT, os_toast_shown: true });
    expect(useApp.getState().scheduledToasts).toHaveLength(0);
    expect(useApp.getState().lastScheduled?.name).toBe('Veille technologique');
  });
});
