import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { MissionControls } from '@/components/dashboard/MissionControls';
import { MissionStatus } from '@/types/mission';

// ── Helpers ───────────────────────────────────────────────────────────────────

const NOOP = vi.fn();

function renderControls(
  status: MissionStatus,
  opts: {
    missionId?: string;
    elapsedSeconds?: number;
    isLoading?: boolean;
    error?: string | null;
    canReplay?: boolean;
    onReplay?: () => void;
  } = {},
) {
  return render(
    <MissionControls
      status={status}
      missionId={opts.missionId ?? ''}
      elapsedSeconds={opts.elapsedSeconds ?? 0}
      onStart={NOOP}
      onPause={NOOP}
      onResume={NOOP}
      onEnd={NOOP}
      isLoading={opts.isLoading}
      error={opts.error}
      canReplay={opts.canReplay}
      onReplay={opts.onReplay}
    />,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('MissionControls — basic rendering', () => {
  it('renders without crashing', () => {
    expect(() => renderControls(MissionStatus.IDLE)).not.toThrow();
  });

  it('has correct testid', () => {
    renderControls(MissionStatus.IDLE);
    expect(screen.getByTestId('mission-controls')).toBeInTheDocument();
  });

  it('shows status label', () => {
    renderControls(MissionStatus.ACTIVE);
    expect(screen.getByText('MISSION ACTIVE')).toBeInTheDocument();
  });

  it('shows mission ID when provided', () => {
    renderControls(MissionStatus.ACTIVE, { missionId: 'abc12345-xxxx' });
    expect(screen.getByText('abc12345…')).toBeInTheDocument();
  });

  it('does not show timer when status is IDLE', () => {
    renderControls(MissionStatus.IDLE, { elapsedSeconds: 100 });
    expect(screen.queryByTestId('mission-timer')).not.toBeInTheDocument();
  });

  it('shows timer when status is ACTIVE', () => {
    renderControls(MissionStatus.ACTIVE, { elapsedSeconds: 125 });
    expect(screen.getByTestId('mission-timer')).toBeInTheDocument();
    expect(screen.getByTestId('mission-timer')).toHaveTextContent('00:02:05');
  });

  it('shows timer when status is PAUSED', () => {
    renderControls(MissionStatus.PAUSED, { elapsedSeconds: 60 });
    expect(screen.getByTestId('mission-timer')).toBeInTheDocument();
  });

  it('shows timer when status is ENDED', () => {
    renderControls(MissionStatus.ENDED, { elapsedSeconds: 3723 });
    expect(screen.getByTestId('mission-timer')).toHaveTextContent('01:02:03');
  });
});

describe('MissionControls — buttons by status', () => {
  it('shows START button when IDLE', () => {
    renderControls(MissionStatus.IDLE);
    expect(screen.getByTestId('btn-start')).toBeInTheDocument();
  });

  it('shows PAUSE and END buttons when ACTIVE', () => {
    renderControls(MissionStatus.ACTIVE);
    expect(screen.getByTestId('btn-pause')).toBeInTheDocument();
    expect(screen.getByTestId('btn-end')).toBeInTheDocument();
  });

  it('shows RESUME and END buttons when PAUSED', () => {
    renderControls(MissionStatus.PAUSED);
    expect(screen.getByTestId('btn-resume')).toBeInTheDocument();
    expect(screen.getByTestId('btn-end')).toBeInTheDocument();
  });

  it('shows NEW MISSION button when ENDED', () => {
    renderControls(MissionStatus.ENDED);
    expect(screen.getByTestId('btn-new-mission')).toBeInTheDocument();
    expect(screen.queryByTestId('btn-start')).not.toBeInTheDocument();
    expect(screen.queryByTestId('btn-pause')).not.toBeInTheDocument();
    expect(screen.queryByTestId('btn-end')).not.toBeInTheDocument();
  });

  it('calls onStart when NEW MISSION clicked from ENDED', () => {
    const onStart = vi.fn();
    render(
      <MissionControls
        status={MissionStatus.ENDED}
        missionId=""
        elapsedSeconds={0}
        onStart={onStart}
        onPause={NOOP}
        onResume={NOOP}
        onEnd={NOOP}
      />,
    );
    fireEvent.click(screen.getByTestId('btn-new-mission'));
    expect(onStart).toHaveBeenCalledOnce();
  });
});

describe('MissionControls — button callbacks', () => {
  it('calls onStart when START clicked', () => {
    const onStart = vi.fn();
    render(
      <MissionControls
        status={MissionStatus.IDLE}
        missionId=""
        elapsedSeconds={0}
        onStart={onStart}
        onPause={NOOP}
        onResume={NOOP}
        onEnd={NOOP}
      />,
    );
    fireEvent.click(screen.getByTestId('btn-start'));
    expect(onStart).toHaveBeenCalledOnce();
  });

  it('calls onPause when PAUSE clicked', () => {
    const onPause = vi.fn();
    render(
      <MissionControls
        status={MissionStatus.ACTIVE}
        missionId=""
        elapsedSeconds={0}
        onStart={NOOP}
        onPause={onPause}
        onResume={NOOP}
        onEnd={NOOP}
      />,
    );
    fireEvent.click(screen.getByTestId('btn-pause'));
    expect(onPause).toHaveBeenCalledOnce();
  });

  it('calls onResume when RESUME clicked', () => {
    const onResume = vi.fn();
    render(
      <MissionControls
        status={MissionStatus.PAUSED}
        missionId=""
        elapsedSeconds={0}
        onStart={NOOP}
        onPause={NOOP}
        onResume={onResume}
        onEnd={NOOP}
      />,
    );
    fireEvent.click(screen.getByTestId('btn-resume'));
    expect(onResume).toHaveBeenCalledOnce();
  });

  it('calls onEnd when END clicked (from ACTIVE)', () => {
    const onEnd = vi.fn();
    render(
      <MissionControls
        status={MissionStatus.ACTIVE}
        missionId=""
        elapsedSeconds={0}
        onStart={NOOP}
        onPause={NOOP}
        onResume={NOOP}
        onEnd={onEnd}
      />,
    );
    fireEvent.click(screen.getByTestId('btn-end'));
    expect(onEnd).toHaveBeenCalledOnce();
  });
});

describe('MissionControls — loading and error states', () => {
  it('disables buttons when loading', () => {
    renderControls(MissionStatus.ACTIVE, { isLoading: true });
    expect(screen.getByTestId('btn-pause')).toBeDisabled();
    expect(screen.getByTestId('btn-end')).toBeDisabled();
  });

  it('shows error message when error is provided', () => {
    renderControls(MissionStatus.ACTIVE, { error: 'Request failed' });
    expect(screen.getByRole('alert')).toHaveTextContent('Request failed');
  });

  it('does not show error when error is null', () => {
    renderControls(MissionStatus.ACTIVE, { error: null });
    expect(screen.queryByRole('alert')).not.toBeInTheDocument();
  });
});

describe('MissionControls — REPLAY button', () => {
  it('shows REPLAY button in ENDED state when canReplay=true and onReplay provided', () => {
    renderControls(MissionStatus.ENDED, { canReplay: true, onReplay: NOOP });
    expect(screen.getByTestId('btn-replay')).toBeInTheDocument();
  });

  it('does not show REPLAY button when canReplay=false', () => {
    renderControls(MissionStatus.ENDED, { canReplay: false, onReplay: NOOP });
    expect(screen.queryByTestId('btn-replay')).not.toBeInTheDocument();
  });

  it('does not show REPLAY button when onReplay is not provided', () => {
    renderControls(MissionStatus.ENDED, { canReplay: true });
    expect(screen.queryByTestId('btn-replay')).not.toBeInTheDocument();
  });

  it('does not show REPLAY button in ACTIVE state', () => {
    renderControls(MissionStatus.ACTIVE, { canReplay: true, onReplay: NOOP });
    expect(screen.queryByTestId('btn-replay')).not.toBeInTheDocument();
  });

  it('does not show REPLAY button in IDLE state', () => {
    renderControls(MissionStatus.IDLE, { canReplay: true, onReplay: NOOP });
    expect(screen.queryByTestId('btn-replay')).not.toBeInTheDocument();
  });

  it('calls onReplay when REPLAY button is clicked', () => {
    const onReplay = vi.fn();
    renderControls(MissionStatus.ENDED, { canReplay: true, onReplay });
    fireEvent.click(screen.getByTestId('btn-replay'));
    expect(onReplay).toHaveBeenCalledOnce();
  });

  it('REPLAY button is disabled when isLoading=true', () => {
    renderControls(MissionStatus.ENDED, { canReplay: true, onReplay: NOOP, isLoading: true });
    expect(screen.getByTestId('btn-replay')).toBeDisabled();
  });

  it('shows both NEW MISSION and REPLAY buttons in ENDED state', () => {
    renderControls(MissionStatus.ENDED, { canReplay: true, onReplay: NOOP });
    expect(screen.getByTestId('btn-new-mission')).toBeInTheDocument();
    expect(screen.getByTestId('btn-replay')).toBeInTheDocument();
  });

  it('REPLAY button has accessible aria-label', () => {
    renderControls(MissionStatus.ENDED, { canReplay: true, onReplay: NOOP });
    expect(screen.getByRole('button', { name: /replay mission/i })).toBeInTheDocument();
  });
});

describe('MissionControls — accessibility', () => {
  it('has accessible button labels', () => {
    renderControls(MissionStatus.ACTIVE);
    expect(screen.getByRole('button', { name: /pause mission/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /end mission/i })).toBeInTheDocument();
  });

  it('timer has accessible aria-label', () => {
    renderControls(MissionStatus.ACTIVE, { elapsedSeconds: 65 });
    const timer = screen.getByTestId('mission-timer');
    expect(timer).toHaveAttribute('aria-label', expect.stringContaining('Elapsed time'));
  });
});
