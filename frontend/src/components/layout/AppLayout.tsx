/**
 * AppLayout — the application shell.
 *
 * Layout (top to bottom):
 *
 *   ┌─ ConnectionBanner (shown only when WebSocket not connected) ─────────┐
 *   ├─ TopNavigation ──────────────────────────────────────────────────────┤
 *   ├─ MainWorkspace ──────────────────┬─ RightSidebar ───────────────────┤
 *   │  TacticalMap                     │  AlertPanel                      │
 *   │  ActivityFeed                    │  DroneStatus                     │
 *   │                                  │  VictimSignals                   │
 *   ├──────────────────────────────────┴──────────────────────────────────┤
 *   └─ BottomTimeline ─────────────────────────────────────────────────────┘
 *
 * No scrolling on the outer shell. Each panel manages its own internal scroll.
 */

import { useCallback } from 'react';
import { TopNavigation }    from './TopNavigation';
import { MainWorkspace }    from './MainWorkspace';
import { RightSidebar }     from './RightSidebar';
import { BottomTimeline }   from './BottomTimeline';
import { ConnectionBanner } from '@/components/dashboard/ConnectionBanner';
import { useMissionStore }  from '@/stores/missionStore';
import { useWebSocket }     from '@/hooks/useWebSocket';
import { useReplayEngine }  from '@/hooks/useReplayEngine';

export function AppLayout() {
  const wsStatus          = useMissionStore((s) => s.wsStatus);
  const reconnectAttempts = useMissionStore((s) => s.reconnectAttempts);
  const { reconnect }     = useWebSocket();

  useReplayEngine();

  const handleReconnect = useCallback(() => {
    reconnect();
  }, [reconnect]);

  return (
    <div
      data-testid="app-layout"
      className="flex h-screen flex-col overflow-hidden bg-bg-base text-text-primary"
    >
      <ConnectionBanner
        wsStatus={wsStatus}
        reconnectAttempts={reconnectAttempts}
        onReconnect={handleReconnect}
      />

      <TopNavigation />

      {/* Content area: main workspace + right sidebar */}
      <div className="flex min-h-0 flex-1">
        <MainWorkspace />
        <RightSidebar />
      </div>

      <BottomTimeline />
    </div>
  );
}
