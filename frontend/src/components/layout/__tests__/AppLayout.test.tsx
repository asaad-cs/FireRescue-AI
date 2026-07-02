import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { AppLayout } from '@/components/layout/AppLayout';
import { useMissionStore } from '@/stores/missionStore';

// Mock WebSocket to prevent real connections during layout tests
beforeEach(() => {
  vi.stubGlobal('WebSocket', class MockWebSocket {
    onopen = null;
    onclose = null;
    onmessage = null;
    onerror = null;
    close = vi.fn();
    constructor(_url: string) {}
  });

  // Reset store to clean state
  const store = useMissionStore.getState();
  store.clearMissionState();
  store.setWsStatus('disconnected');
  store.resetReconnectAttempts();
});

afterEach(() => {
  vi.unstubAllGlobals();
});

function renderLayout() {
  return render(
    <MemoryRouter>
      <AppLayout />
    </MemoryRouter>,
  );
}

describe('AppLayout — shell structure', () => {
  it('renders without crashing', () => {
    expect(() => renderLayout()).not.toThrow();
  });

  it('renders the app layout root element', () => {
    renderLayout();
    expect(screen.getByTestId('app-layout')).toBeInTheDocument();
  });

  it('renders the top navigation region', () => {
    renderLayout();
    expect(screen.getByTestId('top-navigation')).toBeInTheDocument();
  });

  it('renders the main workspace region', () => {
    renderLayout();
    expect(screen.getByTestId('main-workspace')).toBeInTheDocument();
  });

  it('renders the right sidebar region', () => {
    renderLayout();
    expect(screen.getByTestId('right-sidebar')).toBeInTheDocument();
  });

  it('renders the bottom timeline region', () => {
    renderLayout();
    expect(screen.getByTestId('bottom-timeline')).toBeInTheDocument();
  });

  it('renders the application name', () => {
    renderLayout();
    expect(screen.getByText('FIRERESCUE AI')).toBeInTheDocument();
  });

  it('renders the connection indicator', () => {
    renderLayout();
    expect(screen.getByTestId('connection-indicator')).toBeInTheDocument();
  });

  it('connection indicator shows DISCONNECTED initially', () => {
    renderLayout();
    expect(screen.getByText('DISCONNECTED')).toBeInTheDocument();
  });

  it('renders the tactical map placeholder', () => {
    renderLayout();
    expect(screen.getByTestId('tactical-map')).toBeInTheDocument();
  });

  it('renders the alert panel placeholder', () => {
    renderLayout();
    expect(screen.getByTestId('alert-panel')).toBeInTheDocument();
  });

  it('renders the drone status placeholder', () => {
    renderLayout();
    expect(screen.getByTestId('drone-status')).toBeInTheDocument();
  });

  it('renders the victim signals placeholder', () => {
    renderLayout();
    expect(screen.getByTestId('victim-signals')).toBeInTheDocument();
  });

  it('renders the mission timeline placeholder', () => {
    renderLayout();
    expect(screen.getByTestId('mission-timeline')).toBeInTheDocument();
  });

  it('renders mission controls placeholder', () => {
    renderLayout();
    expect(screen.getByTestId('mission-controls')).toBeInTheDocument();
  });
});
