import { NavLink, useLocation } from 'react-router-dom';
import useAppStore from '../../store/appStore';

const NAV = [
  { path: '/', exact: true, label: 'Map', icon: '🗺️' },
  { path: '/alerts', label: 'Alerts', icon: '🔔' },
  { path: '/analytics', label: 'Stats', icon: '📊' },
  { path: '/settings', label: 'Settings', icon: '⚙️' },
];

export default function MobileNav() {
  const location = useLocation();
  const alerts = useAppStore((s) => s.alerts);
  const newCount = (Array.isArray(alerts) ? alerts : []).filter((a) => a?.status === 'new').length;

  return (
    <nav
      className="md:hidden fixed bottom-0 left-0 right-0 z-[2000] border-t border-slate-200 bg-white/95 backdrop-blur-md safe-area-pb"
      aria-label="Main navigation"
    >
      <div className="grid grid-cols-4 h-14">
        {NAV.map((item) => {
          const isActive = item.exact
            ? location.pathname === item.path
            : location.pathname.startsWith(item.path);
          return (
            <NavLink
              key={item.path}
              to={item.path}
              end={item.exact}
              className={[
                'flex flex-col items-center justify-center gap-0.5 text-[10px] font-semibold transition-colors relative',
                isActive ? 'text-forest-700' : 'text-slate-500',
              ].join(' ')}
            >
              <span className="text-base leading-none" aria-hidden>
                {item.icon}
              </span>
              <span>{item.label}</span>
              {item.path === '/alerts' && newCount > 0 && (
                <span className="absolute top-1 right-[calc(50%-20px)] min-w-[16px] h-4 px-1 rounded-full bg-red-500 text-white text-[9px] font-bold flex items-center justify-center">
                  {newCount > 9 ? '9+' : newCount}
                </span>
              )}
            </NavLink>
          );
        })}
      </div>
    </nav>
  );
}
