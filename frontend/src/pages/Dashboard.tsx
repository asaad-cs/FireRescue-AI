/**
 * Dashboard page — renders the application shell.
 *
 * The WebSocket connection lifecycle is managed by AppLayout, which also
 * provides the ConnectionBanner's reconnect callback.
 */

import { AppLayout } from '@/components/layout/AppLayout';

export function Dashboard() {
  return <AppLayout />;
}
