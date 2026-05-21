import useAppStore from '../../store/appStore';
import { format } from 'date-fns';

export default function StatusBar() {
  const { wsConnected, systemHealth, lastScanAt } = useAppStore();

  const dbStatus = systemHealth?.services?.database;
  const schedulerStatus = systemHealth?.services?.scheduler;

  return (
    <div
      className="hidden md:flex items-center justify-between px-4 lg:px-6 py-1.5 text-xs border-t border-slate-200 shrink-0"
      style={{ background: '#f8fafc', minHeight: '32px' }}
    >
      <div className="flex items-center gap-3 lg:gap-4 min-w-0 overflow-x-auto">
        <div className="flex items-center gap-1.5">
          <span className={`status-dot ${wsConnected ? 'connected' : 'offline'}`} />
          <span className={wsConnected ? 'text-green-600 font-medium' : 'text-slate-400'}>
            {wsConnected ? 'Live' : 'Offline'}
          </span>
        </div>

        {dbStatus && (
          <div className="flex items-center gap-1.5 text-slate-500">
            <span className={`status-dot ${dbStatus === 'connected' ? 'connected' : 'offline'}`} />
            <span>DB: {dbStatus === 'connected' ? 'Connected' : 'Error'}</span>
          </div>
        )}

        {schedulerStatus && (
          <div className="flex items-center gap-1.5 text-slate-500">
            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
            Scheduler: {schedulerStatus}
          </div>
        )}
      </div>

      {/* Right: Last scan */}
      <div className="text-slate-400">
        {lastScanAt
          ? `Last scan: ${format(new Date(lastScanAt), 'MMM d, HH:mm')}`
          : 'No scan yet'
        }
      </div>
    </div>
  );
}
