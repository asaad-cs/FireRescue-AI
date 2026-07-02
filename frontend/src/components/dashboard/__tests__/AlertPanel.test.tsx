import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { AlertPanel } from '@/components/dashboard/AlertPanel';
import { AlertLevel, AlertType, type Alert } from '@/types/mission';

// ── Helpers ───────────────────────────────────────────────────────────────────

let idCounter = 0;

function makeAlert(overrides: Partial<Alert> = {}): Alert {
  return {
    alert_id: `alert-${++idCounter}`,
    mission_id: 'mission-1',
    zone_id: 'A1',
    alert_type: AlertType.HAZARD_ELEVATED,
    level: AlertLevel.INFO,
    message: 'Test alert',
    triggered_at: new Date().toISOString(),
    ...overrides,
  };
}

function renderPanel(
  alerts: Alert[] = [],
  acknowledgedAlertIds: string[] = [],
  onAcknowledge = vi.fn(),
) {
  return render(
    <AlertPanel
      alerts={alerts}
      alertCount={alerts.length}
      acknowledgedAlertIds={acknowledgedAlertIds}
      onAcknowledge={onAcknowledge}
    />,
  );
}

// ── Tests ─────────────────────────────────────────────────────────────────────

describe('AlertPanel — basic rendering', () => {
  it('renders without crashing', () => {
    expect(() => renderPanel()).not.toThrow();
  });

  it('has correct testid', () => {
    renderPanel();
    expect(screen.getByTestId('alert-panel')).toBeInTheDocument();
  });

  it('shows empty state when no alerts', () => {
    renderPanel();
    expect(screen.getByText('No active alerts')).toBeInTheDocument();
  });

  it('shows total count in header', () => {
    const alerts = [makeAlert(), makeAlert()];
    renderPanel(alerts);
    expect(screen.getByText('2 total')).toBeInTheDocument();
  });
});

describe('AlertPanel — alert rendering', () => {
  it('renders each alert as a list item', () => {
    const alerts = [makeAlert({ alert_id: 'a1' }), makeAlert({ alert_id: 'a2' })];
    renderPanel(alerts);
    expect(screen.getByTestId('alert-item-a1')).toBeInTheDocument();
    expect(screen.getByTestId('alert-item-a2')).toBeInTheDocument();
  });

  it('shows alert message', () => {
    const alerts = [makeAlert({ message: 'Hazard detected in zone B2' })];
    renderPanel(alerts);
    expect(screen.getByText('Hazard detected in zone B2')).toBeInTheDocument();
  });

  it('shows alert level badge', () => {
    const alerts = [makeAlert({ level: AlertLevel.CRITICAL })];
    renderPanel(alerts);
    expect(screen.getByText('CRITICAL')).toBeInTheDocument();
  });

  it('shows VICTIM SIGNAL label for victim alerts', () => {
    const alerts = [
      makeAlert({
        alert_type: AlertType.VICTIM_DETECTED,
        level: AlertLevel.WARNING,
      }),
    ];
    renderPanel(alerts);
    expect(screen.getByText('VICTIM SIGNAL')).toBeInTheDocument();
  });
});

describe('AlertPanel — acknowledgement', () => {
  it('shows ACK button for CRITICAL alerts', () => {
    const alert = makeAlert({ alert_id: 'crit-1', level: AlertLevel.CRITICAL });
    renderPanel([alert]);
    expect(screen.getByTestId('ack-alert-crit-1')).toBeInTheDocument();
  });

  it('shows ACK button for EMERGENCY alerts', () => {
    const alert = makeAlert({ alert_id: 'emg-1', level: AlertLevel.EMERGENCY });
    renderPanel([alert]);
    expect(screen.getByTestId('ack-alert-emg-1')).toBeInTheDocument();
  });

  it('does not show ACK button for INFO alerts', () => {
    const alert = makeAlert({ alert_id: 'info-1', level: AlertLevel.INFO });
    renderPanel([alert]);
    expect(screen.queryByTestId('ack-alert-info-1')).not.toBeInTheDocument();
  });

  it('calls onAcknowledge when ACK button clicked', () => {
    const onAcknowledge = vi.fn();
    const alert = makeAlert({ alert_id: 'crit-2', level: AlertLevel.CRITICAL });
    renderPanel([alert], [], onAcknowledge);
    fireEvent.click(screen.getByTestId('ack-alert-crit-2'));
    expect(onAcknowledge).toHaveBeenCalledWith('crit-2');
  });

  it('hides ACK button for acknowledged CRITICAL alerts', () => {
    const alert = makeAlert({ alert_id: 'crit-3', level: AlertLevel.CRITICAL });
    renderPanel([alert], ['crit-3']);
    expect(screen.queryByTestId('ack-alert-crit-3')).not.toBeInTheDocument();
  });

  it('shows unack count badge when critical alerts need acknowledgement', () => {
    const alerts = [
      makeAlert({ level: AlertLevel.CRITICAL }),
      makeAlert({ level: AlertLevel.EMERGENCY }),
    ];
    renderPanel(alerts);
    expect(screen.getByText('2 UNACK')).toBeInTheDocument();
  });

  it('hides unack badge when all critical/emergency alerts are acknowledged', () => {
    const alert = makeAlert({ alert_id: 'c1', level: AlertLevel.CRITICAL });
    renderPanel([alert], ['c1']);
    expect(screen.queryByText(/UNACK/)).not.toBeInTheDocument();
  });
});

describe('AlertPanel — sort order', () => {
  it('EMERGENCY alerts appear before CRITICAL', () => {
    const alerts = [
      makeAlert({ alert_id: 'crit', level: AlertLevel.CRITICAL, message: 'Critical msg' }),
      makeAlert({ alert_id: 'emg', level: AlertLevel.EMERGENCY, message: 'Emergency msg' }),
    ];
    renderPanel(alerts);
    const items = screen.getAllByRole('listitem');
    const firstText = items[0].textContent ?? '';
    expect(firstText).toContain('Emergency msg');
  });

  it('WARNING appears before INFO', () => {
    const alerts = [
      makeAlert({ alert_id: 'info', level: AlertLevel.INFO, message: 'Info msg' }),
      makeAlert({ alert_id: 'warn', level: AlertLevel.WARNING, message: 'Warning msg' }),
    ];
    renderPanel(alerts);
    const items = screen.getAllByRole('listitem');
    const firstText = items[0].textContent ?? '';
    expect(firstText).toContain('Warning msg');
  });

  it('acknowledged CRITICAL appears after WARNING', () => {
    const critAlert = makeAlert({ alert_id: 'crit', level: AlertLevel.CRITICAL, message: 'Crit' });
    const warnAlert = makeAlert({ alert_id: 'warn', level: AlertLevel.WARNING, message: 'Warn' });
    renderPanel([critAlert, warnAlert], ['crit']);
    const items = screen.getAllByRole('listitem');
    // Warning should come before acknowledged critical
    const firstText = items[0].textContent ?? '';
    expect(firstText).toContain('Warn');
  });
});
