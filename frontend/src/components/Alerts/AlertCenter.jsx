import { useEffect, useState, useCallback, useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { formatDistanceToNow, isValid } from 'date-fns';
import { alertsApi } from '../../services/api';
import useAppStore from '../../store/appStore';
import { useZones } from '../../hooks/useZones';
import AlertCard from './AlertCard';

const SEVERITY_OPTIONS = ['critical', 'high', 'medium', 'low'];

const INITIAL_STATS = {
  total: 0,
  new: 0,
  acknowledged: 0,
  resolved: 0,
};

function Pill({ active, children, count, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={[
        'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-semibold border transition-colors',
        active
          ? 'bg-emerald-600 text-white border-emerald-600 shadow-sm'
          : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50',
      ].join(' ')}
    >
      {children}
      {typeof count === 'number' && Number.isFinite(count) ? (
        <span
          className={[
            'tabular-nums px-1.5 py-0.5 rounded-md text-[10px]',
            active ? 'bg-white/20' : 'bg-slate-100',
          ].join(' ')}
        >
          {count}
        </span>
      ) : null}
    </button>
  );
}

export default function AlertCenter() {
  const {
    alerts,
    alertsTotal,
    alertsLoading,
    alertsError,
    setAlerts,
    setAlertsLoading,
    setAlertsError,
    activeAlertFilters,
    setAlertFilters,
    zones,
  } = useAppStore();

  const { fetchZones } = useZones();

  const safeZones = Array.isArray(zones) ? zones : [];
  const safeAlerts = Array.isArray(alerts) ? alerts : [];

  const [searchParams] = useSearchParams();
  const searchKey = useMemo(() => searchParams.toString(), [searchParams]);

  const [page, setPage] = useState(0);
  const PAGE_SIZE = 20;
  const [stats, setStats] = useState(INITIAL_STATS);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [lastSyncAt, setLastSyncAt] = useState(null);

  /* Ensure zone labels in filters & alerts work */
  useEffect(() => {
    fetchZones().catch(() => {});
  }, [fetchZones]);

  /* Deep-link (?zone_id= &severity= &status=): stable key + skip redundant store updates */
  useEffect(() => {
    const sp = new URLSearchParams(searchKey);
    const updates = {};
    if (sp.has('zone_id')) updates.zone_id = sp.get('zone_id') ?? '';
    if (sp.has('severity')) updates.severity = sp.get('severity') ?? '';
    if (sp.has('status')) updates.status = sp.get('status') ?? '';
    if (Object.keys(updates).length === 0) return;

    const cur = useAppStore.getState().activeAlertFilters;
    const changed = Object.keys(updates).some((k) => cur[k] !== updates[k]);
    if (changed) useAppStore.getState().setAlertFilters(updates);
  }, [searchKey]);

  const fetchSummary = useCallback(async () => {
    try {
      setSummaryLoading(true);
      const res = await alertsApi.summary();
      const d = res?.data?.data;
      setStats({
        total: Number.isFinite(Number(d?.total)) ? Number(d.total) : 0,
        new: Number.isFinite(Number(d?.new)) ? Number(d.new) : 0,
        acknowledged: Number.isFinite(Number(d?.acknowledged)) ? Number(d.acknowledged) : 0,
        resolved: Number.isFinite(Number(d?.resolved)) ? Number(d.resolved) : 0,
      });
    } catch {
      /* non-fatal: list still renders */
      setStats(INITIAL_STATS);
    } finally {
      setSummaryLoading(false);
    }
  }, []);

  const fetchAlerts = useCallback(async () => {
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
      const body = res?.data ?? res;
      const payload = body?.data;
      const list = Array.isArray(payload?.alerts) ? payload.alerts : [];
      const total = typeof payload?.total === 'number' ? payload.total : Number(payload?.total ?? 0);

      setAlerts(list, Number.isFinite(total) ? total : list.length);
      setLastSyncAt(new Date());
    } catch (err) {
      setAlerts([], 0);
      setAlertsError(err.message || 'Failed to load alerts');
    } finally {
      setAlertsLoading(false);
    }
  }, [
    PAGE_SIZE,
    activeAlertFilters.zone_id,
    activeAlertFilters.severity,
    activeAlertFilters.status,
    page,
    setAlerts,
    setAlertsError,
    setAlertsLoading,
  ]);

  /* Load list whenever filters/page change */
  useEffect(() => {
    fetchAlerts();
  }, [fetchAlerts]);

  /* Summary once on mount + periodically light refresh when tab focused */
  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const handleRefreshAll = async () => {
    await Promise.all([fetchSummary(), fetchAlerts()]);
  };

  const handleQuickStatus = (value) => {
    setAlertFilters({ status: value });
    setPage(0);
  };

  const handleFilterChange = (key, value) => {
    setAlertFilters({ [key]: value });
    setPage(0);
  };

  const handleStatusChanged = () => {
    fetchSummary();
    fetchAlerts();
  };

  const totalPages = Math.ceil(alertsTotal / PAGE_SIZE) || 1;
  const hasAlerts = safeAlerts.length > 0;
  const isFiltered =
    !!(activeAlertFilters.zone_id ||
      activeAlertFilters.severity ||
      activeAlertFilters.status);

  return (
    <div className="flex flex-col flex-1 min-h-0 w-full overflow-hidden bg-slate-50/80">
      {/* Command bar */}
      <div className="shrink-0 border-b border-slate-200 bg-white">
        <div className="px-3 sm:px-6 pt-4 sm:pt-5 pb-3">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <h2 className="text-base font-bold text-slate-900 tracking-tight">Alert inbox</h2>
              <p className="text-xs text-slate-500 mt-1 max-w-xl leading-relaxed">
                Vegetation change events from Sentinel-2 monitoring. Acknowledge items you&apos;re reviewing, resolve when cleared.
              </p>
            </div>
            <button
              type="button"
              onClick={() => handleRefreshAll()}
              disabled={alertsLoading || summaryLoading}
              className="btn-secondary flex items-center gap-2 text-sm shrink-0"
            >
              {alertsLoading || summaryLoading ? (
                <>
                  <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                    />
                  </svg>
                  Syncing…
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  Refresh
                </>
              )}
            </button>
          </div>

          {/* KPI pills */}
          <div className="flex flex-wrap items-center gap-2 mt-5">
            <Pill
              active={activeAlertFilters.status === ''}
              count={stats.total}
              onClick={() => handleQuickStatus('')}
            >
              All
            </Pill>
            <Pill
              active={activeAlertFilters.status === 'new'}
              count={stats.new}
              onClick={() => handleQuickStatus('new')}
            >
              New
            </Pill>
            <Pill
              active={activeAlertFilters.status === 'acknowledged'}
              count={stats.acknowledged}
              onClick={() => handleQuickStatus('acknowledged')}
            >
              Acknowledged
            </Pill>
            <Pill
              active={activeAlertFilters.status === 'resolved'}
              count={stats.resolved}
              onClick={() => handleQuickStatus('resolved')}
            >
              Resolved
            </Pill>
            {lastSyncAt && isValid(lastSyncAt) ? (
              <span className="text-[11px] text-slate-400 ml-auto tabular-nums">
                Updated {formatDistanceToNow(lastSyncAt, { addSuffix: true })}
              </span>
            ) : null}
          </div>
        </div>

        {/* Dropdown filters */}
        <div className="flex flex-wrap items-center gap-2 sm:gap-3 px-3 sm:px-6 py-3 border-t border-slate-100 bg-slate-50/60">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Filters</span>

          <select
            className="input !w-auto text-sm py-1.5 min-w-[140px]"
            aria-label="Filter by zone"
            value={activeAlertFilters.zone_id}
            onChange={(e) => handleFilterChange('zone_id', e.target.value)}
          >
            <option value="">All zones</option>
            {safeZones.map((z) => (
              <option key={z._id} value={z._id}>{z.name}</option>
            ))}
          </select>

          <select
            className="input !w-auto text-sm py-1.5"
            aria-label="Filter by severity"
            value={activeAlertFilters.severity}
            onChange={(e) => handleFilterChange('severity', e.target.value)}
          >
            <option value="">Any severity</option>
            {SEVERITY_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s.charAt(0).toUpperCase() + s.slice(1)}
              </option>
            ))}
          </select>

          <button
            type="button"
            onClick={() => {
              setAlertFilters({ zone_id: '', severity: '', status: '' });
              setPage(0);
            }}
            className="text-xs font-medium text-emerald-700 hover:text-emerald-900"
          >
            Reset filters
          </button>

          <div className="ml-auto text-xs text-slate-500 tabular-nums">
            Showing <strong className="text-slate-800">{safeAlerts.length}</strong>
            {' of '}
            <strong className="text-slate-800">{alertsTotal}</strong> · Page {Math.min(page + 1, totalPages)} /
            {' '}{totalPages}
          </div>
        </div>
      </div>

      {/* Scrollable feed */}
      <div className="flex-1 overflow-y-auto px-3 sm:px-6 py-4 sm:py-5">
        {alertsLoading && !hasAlerts && (
          <div className="space-y-4 max-w-4xl">
            {[1, 2, 3].map((i) => (
              <div key={i} className="skeleton h-52 w-full rounded-xl" />
            ))}
          </div>
        )}

        {alertsError && (
          <div className="max-w-lg mx-auto text-center mt-16 py-14 px-6 rounded-2xl border border-red-100 bg-white shadow-sm">
            <div className="text-3xl mb-3" aria-hidden>⚠️</div>
            <p className="font-semibold text-slate-900">Unable to load alerts</p>
            <p className="text-sm text-slate-500 mt-2 leading-relaxed">{alertsError}</p>
            <p className="text-xs text-slate-400 mt-3">
              Check backend is running and <code className="font-mono">VITE_API_URL</code> points to it (default{' '}
              <code className="font-mono">http://localhost:8000</code>).
            </p>
            <button type="button" onClick={fetchAlerts} className="btn-primary mt-6">
              Retry
            </button>
          </div>
        )}

        {!alertsLoading && !alertsError && safeAlerts.length === 0 && (
          <div className="max-w-lg mx-auto text-center mt-12 py-16 px-8 rounded-2xl border border-slate-200 bg-white shadow-sm">
            <div className="text-5xl mb-4" aria-hidden>🛰️</div>
            <p className="font-bold text-slate-900 text-lg leading-snug">
              No alerts yet{isFiltered ? ' for this filter' : ''}
            </p>
            <p className="text-sm text-slate-500 mt-3 leading-relaxed">
              Alerts are created automatically when successive satellite passes show vegetation loss beyond your zone
              thresholds. Make sure predefined zones completed at least two scans over time range.
            </p>
            {isFiltered ? (
              <button
                type="button"
                className="btn-secondary mt-6 text-sm"
                onClick={() => {
                  setAlertFilters({ zone_id: '', severity: '', status: '' });
                  setPage(0);
                }}
              >
                Clear filters & show all
              </button>
            ) : null}
          </div>
        )}

        {!alertsLoading && alertsError === null && hasAlerts && (
          <div className="max-w-4xl space-y-4">
            {safeAlerts.map((alert) => (
              <AlertCard key={alert._id || `alert-${alert.zone_id}-${alert.detected_at}`} alert={alert} onStatusChanged={handleStatusChanged} />
            ))}
          </div>
        )}

        {totalPages > 1 && !alertsError && alertsTotal > PAGE_SIZE ? (
          <div className="max-w-4xl flex items-center justify-center gap-3 mt-8 pt-4 border-t border-slate-200/80">
            <button
              type="button"
              onClick={() => setPage((p) => Math.max(0, p - 1))}
              disabled={page === 0 || alertsLoading}
              className="btn-secondary text-sm py-2 px-4 disabled:opacity-40"
            >
              ← Previous
            </button>
            <span className="text-sm text-slate-600 tabular-nums font-medium">
              Page {page + 1} of {totalPages}
            </span>
            <button
              type="button"
              onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
              disabled={page >= totalPages - 1 || alertsLoading}
              className="btn-secondary text-sm py-2 px-4 disabled:opacity-40"
            >
              Next →
            </button>
          </div>
        ) : null}
      </div>
    </div>
  );
}
