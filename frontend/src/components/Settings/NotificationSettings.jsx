import { useEffect, useState } from 'react';
import useAppStore from '../../store/appStore';
import { healthApi } from '../../services/api';

export default function NotificationSettings() {
  const { systemHealth, setSystemHealth, setLastScanAt, wsConnected } = useAppStore();
  const [loading, setLoading] = useState(false);

  const fetchHealth = async () => {
    setLoading(true);
    try {
      const res = await healthApi.check();
      const data = res.data.data;
      setSystemHealth(data);
      if (data.last_scan_at) setLastScanAt(data.last_scan_at);
    } catch (err) {
      console.error('Health check failed:', err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchHealth();
    const interval = setInterval(fetchHealth, 30000); // refresh every 30s
    return () => clearInterval(interval);
  }, []);

  const services = systemHealth?.services || {};
  const overall = systemHealth?.status || 'unknown';

  const getStatusBadge = (status) => {
    if (status === 'connected' || status === 'running') {
      return <span className="text-xs font-bold text-green-700 bg-green-50 border border-green-200 px-2 py-0.5 rounded-full">● {status}</span>;
    }
    if (status === 'stopped') {
      return <span className="text-xs font-bold text-yellow-700 bg-yellow-50 border border-yellow-200 px-2 py-0.5 rounded-full">● {status}</span>;
    }
    return <span className="text-xs font-bold text-red-700 bg-red-50 border border-red-200 px-2 py-0.5 rounded-full">● {status || 'unknown'}</span>;
  };

  return (
    <div className="space-y-4">
      <div className="card p-5">
        <div className="flex items-center justify-between mb-4">
          <h3 className="font-bold text-slate-800">System Status</h3>
          <button
            onClick={fetchHealth}
            disabled={loading}
            className="btn-ghost text-xs"
          >
            {loading ? 'Refreshing…' : '↻ Refresh'}
          </button>
        </div>

        {/* Overall status */}
        <div className="flex items-center gap-3 mb-4 p-3 rounded-lg bg-slate-50">
          <div className={`w-3 h-3 rounded-full ${overall === 'healthy' ? 'bg-green-500' : 'bg-red-500'} animate-pulse`} />
          <div>
            <div className="font-semibold text-slate-800 text-sm">
              System is{' '}
              <span className={overall === 'healthy' ? 'text-green-700' : 'text-red-700'}>
                {overall}
              </span>
            </div>
            {systemHealth?.timestamp && (
              <div className="text-xs text-slate-500">
                Last checked: {new Date(systemHealth.timestamp).toLocaleTimeString()}
              </div>
            )}
          </div>
        </div>

        {/* Services table */}
        <div className="space-y-2.5">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-slate-700">
              <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582 4 8 4m0 0c4.418 0 8-1.79 8-4" />
              </svg>
              MongoDB Database
            </div>
            {getStatusBadge(services.database)}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-slate-700">
              <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              Redis Cache
            </div>
            {getStatusBadge(services.redis)}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-slate-700">
              <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
              </svg>
              APScheduler
            </div>
            {getStatusBadge(services.scheduler)}
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-sm text-slate-700">
              <svg className="w-4 h-4 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8.111 16.404a5.5 5.5 0 017.778 0M12 20h.01m-7.08-7.071c3.904-3.905 10.236-3.905 14.14 0M1.394 9.393c5.857-5.857 15.355-5.857 21.213 0" />
              </svg>
              WebSocket
            </div>
            {getStatusBadge(wsConnected ? 'connected' : 'disconnected')}
          </div>
        </div>

        {/* Last scan */}
        {systemHealth?.last_scan_at && (
          <div className="mt-4 pt-3 border-t border-slate-100 text-xs text-slate-500">
            Last global scan: {new Date(systemHealth.last_scan_at).toLocaleString()}
          </div>
        )}
      </div>

      {/* Environment info */}
      <div className="card p-5">
        <h3 className="font-bold text-slate-800 mb-3">Configuration</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-500">API Endpoint</span>
            <code className="text-slate-700 text-xs bg-slate-100 px-2 py-0.5 rounded">
              {import.meta.env.VITE_API_URL || 'http://localhost:8000'}
            </code>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-500">WebSocket</span>
            <code className="text-slate-700 text-xs bg-slate-100 px-2 py-0.5 rounded">
              {import.meta.env.VITE_WS_URL || 'ws://localhost:8000'}/ws/alerts
            </code>
          </div>
        </div>
      </div>
    </div>
  );
}
