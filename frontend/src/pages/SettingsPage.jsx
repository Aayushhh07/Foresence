import { useEffect } from 'react';
import { useZones } from '../hooks/useZones';
import ZoneSettings from '../components/Settings/ZoneSettings';
import NotificationSettings from '../components/Settings/NotificationSettings';

export default function SettingsPage() {
  const { fetchZones, zonesLoading } = useZones();

  useEffect(() => {
    fetchZones();
  }, [fetchZones]);

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      <div className="p-3 sm:p-6 space-y-6 sm:space-y-8 max-w-4xl mx-auto w-full">
        {/* Zone Management */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <div>
              <h2 className="text-lg font-bold text-slate-900">Zone Management</h2>
              <p className="text-sm text-slate-500 mt-0.5">
                Configure NDVI thresholds, email alerts, and monitoring schedules per zone.
              </p>
            </div>
            {zonesLoading && (
              <svg className="w-5 h-5 animate-spin text-forest-600" fill="none" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
            )}
          </div>
          <ZoneSettings />
        </section>

        {/* System Status */}
        <section>
          <div className="mb-4">
            <h2 className="text-lg font-bold text-slate-900">System Status</h2>
            <p className="text-sm text-slate-500 mt-0.5">
              Monitor backend services, scheduler, and real-time connection health.
            </p>
          </div>
          <NotificationSettings />
        </section>
      </div>
    </div>
  );
}
