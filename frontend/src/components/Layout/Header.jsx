import { useState } from 'react';
import { useLocation } from 'react-router-dom';
import { toast } from 'react-toastify';
import useAppStore from '../../store/appStore';
import { alertsApi } from '../../services/api';
import { useZones } from '../../hooks/useZones';
import api from '../../services/api';

const PAGE_TITLES = {
  '/': { title: 'Map Dashboard', subtitle: 'Monitor forest zones in real-time' },
  '/alerts': { title: 'Alert Center', subtitle: 'Deforestation detection events' },
  '/analytics': { title: 'Analytics', subtitle: 'NDVI trends and vegetation health' },
  '/settings': { title: 'Settings', subtitle: 'Zone management and configuration' },
};

export default function Header() {
  const location = useLocation();
  const page = PAGE_TITLES[location.pathname] || { title: 'Foresence', subtitle: '' };
  const { zones, alerts, setAlerts } = useAppStore();
  const { fetchZones } = useZones();
  const [seeding, setSeeding] = useState(false);

  const criticalZones = zones.filter((z) => z.status === 'critical').length;
  const newAlerts = alerts.filter((a) => a.status === 'new').length;

  const handleSeedDemo = async () => {
    setSeeding(true);
    try {
      const res = await api.post('/api/demo/seed');
      toast.success(res.data.message || '✅ Demo data seeded!', { autoClose: 5000 });
      // Refresh zones and alerts
      await fetchZones();
      const alertRes = await alertsApi.list({ limit: 50 });
      const data = alertRes.data.data;
      setAlerts(data?.alerts || [], data?.total || 0);
    } catch (err) {
      toast.error('Seed failed: ' + err.message);
    } finally {
      setSeeding(false);
    }
  };

  return (
    <header className="flex items-center justify-between px-6 py-3 bg-white border-b border-slate-200">
      {/* Page Title */}
      <div>
        <h1 className="text-lg font-bold text-slate-900 leading-tight">{page.title}</h1>
        <p className="text-xs text-slate-500">{page.subtitle}</p>
      </div>

      {/* Stats pills + Seed button */}
      <div className="flex items-center gap-3">
        {/* Seed Demo Button */}
        <button
          id="seed-demo-btn"
          onClick={handleSeedDemo}
          disabled={seeding}
          className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-700 disabled:bg-emerald-400 text-white text-xs font-semibold px-3 py-1.5 rounded-full transition-colors shadow-sm"
        >
          {seeding ? (
            <>
              <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
              </svg>
              Seeding...
            </>
          ) : (
            <span>🌱 Seed Demo Data</span>
          )}
        </button>

        {criticalZones > 0 && (
          <div className="flex items-center gap-1.5 bg-red-50 border border-red-200 text-red-700 text-xs font-semibold px-3 py-1.5 rounded-full animate-pulse">
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
            </svg>
            {criticalZones} Critical Zone{criticalZones > 1 ? 's' : ''}
          </div>
        )}

        <div className="flex items-center gap-1.5 bg-slate-100 text-slate-600 text-xs font-semibold px-3 py-1.5 rounded-full">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
          </svg>
          {zones.length} Zone{zones.length !== 1 ? 's' : ''}
        </div>

        {newAlerts > 0 && (
          <div className="flex items-center gap-1.5 bg-orange-50 border border-orange-200 text-orange-700 text-xs font-semibold px-3 py-1.5 rounded-full">
            <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20">
              <path d="M10 2a6 6 0 00-6 6v3.586l-.707.707A1 1 0 004 14h12a1 1 0 00.707-1.707L16 11.586V8a6 6 0 00-6-6zM10 18a3 3 0 01-3-3h6a3 3 0 01-3 3z" />
            </svg>
            {newAlerts} New Alert{newAlerts !== 1 ? 's' : ''}
          </div>
        )}
      </div>
    </header>
  );
}
