import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { alertsApi } from '../../services/api';
import useAppStore from '../../store/appStore';
import AlertCard from './AlertCard';

const SEVERITY_OPTIONS = ['', 'critical', 'high', 'medium', 'low'];
const STATUS_OPTIONS = ['', 'new', 'acknowledged', 'resolved'];

export default function AlertCenter() {
  const {
    alerts, alertsTotal, alertsLoading, alertsError,
    setAlerts, setAlertsLoading, setAlertsError,
    activeAlertFilters, setAlertFilters, zones,
  } = useAppStore();

  const [searchParams, setSearchParams] = useSearchParams();
  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;

  // Sync URL params to filters on mount
  useEffect(() => {
    const zone_id = searchParams.get('zone_id') || '';
    const severity = searchParams.get('severity') || '';
    const status = searchParams.get('status') || '';
    setAlertFilters({ zone_id, severity, status });
  }, []);

  useEffect(() => {
    fetchAlerts();
  }, [activeAlertFilters, page]);

  const fetchAlerts = async () => {
    setAlertsLoading(true);
    setAlertsError(null);
    try {
      const params = {
        limit: PAGE_SIZE,
        skip: page * PAGE_SIZE,
      };
      if (activeAlertFilters.zone_id) params.zone_id = activeAlertFilters.zone_id;
      if (activeAlertFilters.severity) params.severity = activeAlertFilters.severity;
      if (activeAlertFilters.status) params.status = activeAlertFilters.status;

      const res = await alertsApi.list(params);
      setAlerts(res.data.data?.alerts || [], res.data.data?.total || 0);
    } catch (err) {
      setAlertsError(err.message);
    } finally {
      setAlertsLoading(false);
    }
  };

  const handleFilterChange = (key, value) => {
    setAlertFilters({ [key]: value });
    setPage(0);
  };

  const totalPages = Math.ceil(alertsTotal / PAGE_SIZE);

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* ─── Filters ─── */}
      <div className="flex flex-wrap items-center gap-3 px-6 py-4 bg-white border-b border-slate-200">
        <span className="text-sm font-semibold text-slate-700">Filters:</span>

        {/* Zone filter */}
        <select
          className="input !w-auto text-sm py-1.5"
          value={activeAlertFilters.zone_id}
          onChange={(e) => handleFilterChange('zone_id', e.target.value)}
        >
          <option value="">All Zones</option>
          {zones.map((z) => (
            <option key={z._id} value={z._id}>{z.name}</option>
          ))}
        </select>

        {/* Severity filter */}
        <select
          className="input !w-auto text-sm py-1.5"
          value={activeAlertFilters.severity}
          onChange={(e) => handleFilterChange('severity', e.target.value)}
        >
          <option value="">All Severities</option>
          {SEVERITY_OPTIONS.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>

        {/* Status filter */}
        <select
          className="input !w-auto text-sm py-1.5"
          value={activeAlertFilters.status}
          onChange={(e) => handleFilterChange('status', e.target.value)}
        >
          <option value="">All Statuses</option>
          {STATUS_OPTIONS.filter(Boolean).map((s) => (
            <option key={s} value={s}>{s.charAt(0).toUpperCase() + s.slice(1)}</option>
          ))}
        </select>

        <button
          onClick={() => {
            setAlertFilters({ zone_id: '', severity: '', status: '' });
            setPage(0);
          }}
          className="btn-ghost text-xs"
        >
          Clear
        </button>

        <div className="ml-auto text-sm text-slate-500">
          {alertsTotal} alert{alertsTotal !== 1 ? 's' : ''}
          {alertsTotal > 0 && ` · page ${page + 1}/${Math.max(totalPages, 1)}`}
        </div>
      </div>

      {/* ─── Content ─── */}
      <div className="flex-1 overflow-y-auto px-6 py-4">
        {alertsLoading && (
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-48 w-full" />
            ))}
          </div>
        )}

        {alertsError && (
          <div className="flex flex-col items-center py-20 text-center">
            <div className="text-4xl mb-3">⚠️</div>
            <div className="font-semibold text-slate-700">Failed to load alerts</div>
            <div className="text-slate-500 text-sm mt-1">{alertsError}</div>
            <button onClick={fetchAlerts} className="btn-primary mt-4">Retry</button>
          </div>
        )}

        {!alertsLoading && !alertsError && alerts.length === 0 && (
          <div className="flex flex-col items-center py-24 text-center">
            <div className="text-5xl mb-4">🌿</div>
            <div className="font-bold text-slate-700 text-lg">No alerts found</div>
            <div className="text-slate-500 text-sm mt-2 max-w-sm">
              {Object.values(activeAlertFilters).some(Boolean)
                ? 'No alerts match your current filters. Try adjusting them.'
                : 'All monitored zones are healthy. Alerts will appear here when deforestation is detected.'}
            </div>
          </div>
        )}

        {!alertsLoading && !alertsError && alerts.length > 0 && (
          <div className="space-y-3">
            {alerts.map((alert) => (
              <AlertCard key={alert._id} alert={alert} />
            ))}
          </div>
        )}

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-3 mt-6 pt-4 border-t border-slate-100">
            <button
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0}
              className="btn-secondary text-xs py-1.5 px-3 disabled:opacity-40"
            >
              ← Prev
            </button>
            <span className="text-sm text-slate-600">
              Page {page + 1} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1}
              className="btn-secondary text-xs py-1.5 px-3 disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
