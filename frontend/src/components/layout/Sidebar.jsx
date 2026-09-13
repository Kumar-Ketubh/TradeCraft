import { NavLink } from 'react-router-dom';
import { LayoutDashboard, Building2, Search, FileText, Settings, HelpCircle } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function Sidebar() {
  const { currentUser, activeWorkspace } = useAuth();

  const mainNav = [
    { id: 'dashboard', path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'competitors', path: '/competitors', label: 'Competitors', icon: Building2 },
    { id: 'findings', path: '/findings', label: 'Findings', icon: Search },
    { id: 'proposals', path: '/proposals', label: 'Proposals', icon: FileText },
  ];

  const accountNav = [
    { id: 'settings', path: '/settings', label: 'Settings', icon: Settings },
    { id: 'help', path: '/help', label: 'Help & Support', icon: HelpCircle },
  ];

  return (
    <aside className="sidebar">
      <div className="sidebar-header flex items-center justify-between">
        <div className="flex items-center gap-3 overflow-hidden">
          <div className="grid w-8 h-8 shrink-0 place-content-center rounded bg-primary-light shadow-sm">
            <span className="text-primary font-bold">TC</span>
          </div>
          <div className="flex-1 whitespace-nowrap overflow-hidden">
            <h1 className="text-sm font-semibold text-text truncate">TradeCraft</h1>
            <span className="text-[10px] text-muted font-medium uppercase tracking-wider truncate">Intel</span>
          </div>
        </div>
      </div>
      
      <div className="flex flex-col flex-1 overflow-y-auto overflow-x-hidden pt-4">
        <nav className="sidebar-nav space-y-1">
          {mainNav.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.id}
                to={item.path}
                className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
              >
                <div className="grid w-8 place-content-center shrink-0">
                  <Icon size={18} />
                </div>
                <span className="whitespace-nowrap">
                  {item.label}
                </span>
              </NavLink>
            );
          })}
        </nav>

        <div className="px-3 pb-2 pt-6 border-t border-border mt-6">
          <span className="text-[10px] font-semibold text-muted px-2 mb-2 block uppercase tracking-wider">Account</span>
          <nav className="flex flex-col space-y-1">
            {accountNav.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.id}
                  to={item.path}
                  className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
                >
                  <div className="grid w-8 place-content-center shrink-0">
                    <Icon size={18} />
                  </div>
                  <span className="whitespace-nowrap">{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>
      </div>
    </aside>
  );
}
