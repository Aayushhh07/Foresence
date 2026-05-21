import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { snapshotsApi, alertsApi } from '../services/api';
import useAppStore from '../store/appStore';
import NDVIChart from '../components/Analytics/NDVIChart';
import ChangeAreaChart from '../components/Analytics/ChangeAreaChart';

export default function AnalyticsPage() {
  const { zones, snapshots, setSnapshots, setSnapshotsLoading, snapshotsLoading } = useAppStore();
  const [searchParams, setSearchParams] = useSearchParams();
  const [selectedZoneId, setSelectedZoneId] = useState(searchParams.get('zone') || '');
  const [alerts30, setAlerts30] = useState([]);
  const [statsLoading, setStatsLoading] = useState(false);

  useEffect(() => {
    if (selectedZoneId) {
      fetchData(selectedZoneId);
    }
  }, [selectedZoneId]);

  const fetchData = async (zoneId) => {
    setStatsLoading(true);
    setSnapshotsLoading(true);
    try {
      const [snapRes, alertRes] = await Promise.all([
        snapshotsApi.list({
          zone_id: zoneId,
          limit: 90,
        }),
        alertsApi.list({ zone_id: zoneId, limit: 30 }),
      ]);
      setSnapshots(snapRes.data.data || []);
      setAlerts30(alertRes.data.data?.alerts || []);
    } catch (err) {
      console.error('Analytics fetch error:', err.message);
    } finally {
      setStatsLoading(false);
      setSnapshotsLoading(false);
    }
  };

  const handleZoneChange = (id) => {
    setSelectedZoneId(id);
    if (id) setSearchParams({ zone: id });
    else setSearchParams({});
  };

  const selectedZone = zones.find((z) => z._id === selectedZoneId);
  const avgNdvi = snapshots.length
    ? (snapshots.reduce((sum, s) => sum + (s.ndvi_mean || 0), 0) / snapshots.length).toFixed(3)
    : '—';
  const latestNdvi = snapshots.length
    ? snapshots.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))[0]?.ndvi_mean?.toFixed(3)
    : '—';
  const highestConfAlert = alerts30.length
    ? alerts30.reduce((max, a) => a.confidence > (max?.confidence || 0) ? a : max, null)
    : null;

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="p-3 sm:p-6 space-y-4 sm:space-y-6">
        <div className="flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
          <label className="label whitespace-nowrap">Select Zone</label>
          <select
            className="input w-full sm:max-w-xs"
            value={selectedZoneId}
            onChange={(e) => handleZoneChange(e.target.value)}
          >
            <option value="">— Choose a zone —</option>
            {zones.map((z) => (
              <option key={z._id} value={z._id}>{z.name}</option>
            ))}
          </select>
        </div>

        {!selectedZoneId && (
          <div className="flex flex-col items-center py-24 text-center">
            <div className="text-5xl mb-4">📊</div>
            <div className="font-bold text-slate-700 text-lg">Select a zone to view analytics</div>
            <div className="text-slate-500 text-sm mt-2">
              Choose a monitoring zone from the dropdown above to see NDVI trends and change data.
            </div>
          </div>
        )}

        {selectedZoneId && (
          <>
            {/* Stats row */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
              <div className="stat-card">
                <div className="text-xs text-slate-500 font-semibold uppercase tracking-wide">Health Score</div>
                <div className="text-3xl font-black mt-1"
                  style={{ color: selectedZone?.status === 'healthy' ? '#16a34a' : selectedZone?.status === 'warning' ? '#d97706' : '#dc2626' }}>
                  {selectedZone?.health_score ?? '—'}
                </div>
                <div className="text-xs text-slate-400">/100</div>
              </div>
              <div className="stat-card">
                <div className="text-xs text-slate-500 font-semibold uppercase tracking-wide">Latest NDVI</div>
                <div className="text-3xl font-black text-slate-800 mt-1">{latestNdvi}</div>
                <div className="text-xs text-slate-400">Current reading</div>
              </div>
              <div className="stat-card">
                <div className="text-xs text-slate-500 font-semibold uppercase tracking-wide">Avg NDVI (30d)</div>
                <div className="text-3xl font-black text-slate-800 mt-1">{avgNdvi}</div>
                <div className="text-xs text-slate-400">{snapshots.length} snapshots</div>
              </div>
              <div className="stat-card">
                <div className="text-xs text-slate-500 font-semibold uppercase tracking-wide">Total Alerts</div>
                <div className="text-3xl font-black text-slate-800 mt-1">{alerts30.length}</div>
                {highestConfAlert && (
                  <div className="text-xs text-slate-400">
                    Peak: {Math.round(highestConfAlert.confidence * 100)}% conf.
                  </div>
                )}
              </div>
            </div>

            {/* NDVI Chart */}
            <div className="card p-5">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="font-bold text-slate-800">NDVI Trend</h2>
                  <p className="text-xs text-slate-500 mt-0.5">30-day vegetation index with confidence band</p>
                </div>
                {snapshotsLoading && (
                  <svg className="w-5 h-5 animate-spin text-forest-600" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                )}
              </div>
              {snapshotsLoading ? (
                <div className="skeleton h-64 w-full" />
              ) : (
                <NDVIChart snapshots={snapshots} />
              )}
            </div>

            {/* Change Area Chart */}
            <div className="card p-5">
              <h2 className="font-bold text-slate-800 mb-1">Deforestation Events</h2>
              <p className="text-xs text-slate-500 mb-4">Area affected per alert (colored by severity)</p>
              {statsLoading ? (
                <div className="skeleton h-48 w-full" />
              ) : (
                <ChangeAreaChart alerts={alerts30} />
              )}
            </div>
          </>
        )}
      </div>
    </div>
  );
}
