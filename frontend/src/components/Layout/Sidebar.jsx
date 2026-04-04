import { NavLink, useLocation } from 'react-router-dom';
import useAppStore from '../../store/appStore';

const NAV = [
  {
    path: '/',
    exact: true,
    label: 'Map',
    icon: (
      <svg className="sidebar-link-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
      </svg>
    ),
  },
  {
    path: '/alerts',
    label: 'Alerts',
    icon: (
      <svg className="sidebar-link-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
      </svg>
    ),
  },
  {
    path: '/analytics',
    label: 'Analytics',
    icon: (
      <svg className="sidebar-link-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
      </svg>
    ),
  },
  {
    path: '/settings',
    label: 'Settings',
    icon: (
      <svg className="sidebar-link-icon" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
          d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
      </svg>
    ),
  },
];

export default function Sidebar() {
  const { sidebarCollapsed, setSidebarCollapsed, alerts, zones } = useAppStore();
  const newAlertsCount = alerts.filter((a) => a.status === 'new').length;

  return (
    <aside
      className={`h-full flex flex-col transition-all duration-300 ease-in-out
        ${sidebarCollapsed ? 'w-16' : 'w-60'}`}
      style={{ background: '#0f172a', borderRight: '1px solid rgba(255,255,255,0.06)' }}
    >
      {/* Logo */}
      <div className="flex items-center gap-3 px-4 py-5 border-b border-white/10">
        <div className="w-8 h-8 rounded-lg bg-forest-600 flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-white" fill="currentColor" viewBox="0 0 24 24">
            <path d="M17 8C8 10 5.9 16.17 3.82 21.34L5.71 22l1-2.3A4.49 4.49 0 0 0 8 20C19 20 22 3 22 3c-1 2-8 2-8 2s-.56-1.17-1-.94C11 5 8.68 7.61 8 10c1-3 3-5 6-6 0 0-1 2-1 5s3 5 5 5c-1 0-2-1-2-2.5C16 9 17 8 17 8z"/>
          </svg>
        </div>
        {!sidebarCollapsed && (
          <div>
            <div className="text-white font-bold text-base leading-tight">Foresence</div>
            <div className="text-slate-500 text-xs">Deforestation Monitor</div>
          </div>
        )}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className={`ml-auto text-slate-500 hover:text-white transition-colors ${sidebarCollapsed ? 'mx-auto' : ''}`}
          aria-label="Toggle sidebar"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            {sidebarCollapsed
              ? <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              : <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            }
          </svg>
        </button>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-2 py-4 space-y-1">
        {NAV.map((item) => (
          <NavLink
            key={item.path}
            to={item.path}
            end={item.exact}
            className={({ isActive }) =>
              `sidebar-link ${isActive ? 'active' : ''}`
            }
          >
            {item.icon}
            {!sidebarCollapsed && (
              <span className="flex-1">{item.label}</span>
            )}
            {!sidebarCollapsed && item.path === '/alerts' && newAlertsCount > 0 && (
              <span className="bg-red-500 text-white text-xs font-bold px-1.5 py-0.5 rounded-full min-w-[20px] text-center">
                {newAlertsCount > 99 ? '99+' : newAlertsCount}
              </span>
            )}
            {sidebarCollapsed && item.path === '/alerts' && newAlertsCount > 0 && (
              <span className="absolute top-1 right-1 w-2 h-2 bg-red-500 rounded-full" />
            )}
          </NavLink>
        ))}
      </nav>

      {/* Bottom stats */}
      {!sidebarCollapsed && (
        <div className="px-3 pb-4 space-y-2">
          <div className="rounded-lg p-3" style={{ background: 'rgba(255,255,255,0.04)', border: '1px solid rgba(255,255,255,0.08)' }}>
            <div className="text-slate-500 text-xs mb-2 uppercase tracking-wide font-semibold">Quick Stats</div>
            <div className="flex justify-between text-xs">
              <span className="text-slate-400">Zones</span>
              <span className="text-white font-semibold">{zones.length}</span>
            </div>
            <div className="flex justify-between text-xs mt-1">
              <span className="text-slate-400">New Alerts</span>
              <span className={`font-semibold ${newAlertsCount > 0 ? 'text-red-400' : 'text-white'}`}>
                {newAlertsCount}
              </span>
            </div>
          </div>
        </div>
      )}
    </aside>
  );
}
