import { NavLink } from 'react-router-dom';
import { 
  LayoutDashboard, 
  Building2, 
  Search, 
  FileText, 
  Settings, 
  HelpCircle, 
  Sparkles,
  Layers,
  Activity,
  ArrowUpRight
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function Sidebar() {
  const { activeWorkspace } = useAuth();

  const productNav = [
    { id: 'dashboard', path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { id: 'competitors', path: '/competitors', label: 'Competitors', icon: Building2 },
    { id: 'findings', path: '/findings', label: 'Findings', icon: Search, badge: 'Live' },
    { id: 'proposals', path: '/proposals', label: 'Proposals', icon: FileText },
  ];

  const workspaceNav = [
    { id: 'integrations', path: '/competitors', label: 'Sources & Adapters', icon: Layers },
    { id: 'activity', path: '/dashboard', label: 'Scan History', icon: Activity },
  ];

  const adminNav = [
    { id: 'settings', path: '/settings', label: 'Settings', icon: Settings },
    { id: 'help', path: '/help', label: 'Help & Docs', icon: HelpCircle },
  ];

  return (
    <aside className="sidebar flex flex-col justify-between">
      <div>
        {/* Brand Header */}
        <div className="sidebar-header flex items-center gap-3">
          <div className="w-7 h-7 rounded-md bg-blue-600 flex items-center justify-center shadow-xs">
            <span className="text-white text-xs font-bold tracking-tight">TC</span>
          </div>
          <div className="flex flex-col min-w-0">
            <h1 className="text-sm font-bold text-text tracking-tight truncate leading-tight">TradeCraft</h1>
            <span className="text-2xs text-muted font-medium uppercase tracking-wider">Competitive Intel</span>
          </div>
        </div>

        {/* Navigation Categories */}
        <div className="flex flex-col gap-6 pt-4 px-3 overflow-y-auto">
          {/* Section 1: Product / Intelligence */}
          <div>
            <span className="text-2xs font-semibold text-muted px-2.5 mb-1.5 block uppercase tracking-wider">
              Product
            </span>
            <nav className="flex flex-col gap-0.5">
              {productNav.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.id}
                    to={item.path}
                    className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
                  >
                    <Icon size={16} />
                    <span className="flex-1 truncate">{item.label}</span>
                    {item.badge && (
                      <span className="text-2xs font-semibold px-1.5 py-0.2 rounded bg-blue-500/10 text-blue-500 border border-blue-500/20">
                        {item.badge}
                      </span>
                    )}
                  </NavLink>
                );
              })}
            </nav>
          </div>

          {/* Section 2: Workspace */}
          <div>
            <span className="text-2xs font-semibold text-muted px-2.5 mb-1.5 block uppercase tracking-wider">
              Workspace
            </span>
            <nav className="flex flex-col gap-0.5">
              {workspaceNav.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.id}
                    to={item.path}
                    className="sidebar-link"
                  >
                    <Icon size={16} />
                    <span className="flex-1 truncate">{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>
          </div>

          {/* Section 3: Administration */}
          <div>
            <span className="text-2xs font-semibold text-muted px-2.5 mb-1.5 block uppercase tracking-wider">
              Administration
            </span>
            <nav className="flex flex-col gap-0.5">
              {adminNav.map((item) => {
                const Icon = item.icon;
                return (
                  <NavLink
                    key={item.id}
                    to={item.path}
                    className={({ isActive }) => `sidebar-link ${isActive ? 'active' : ''}`}
                  >
                    <Icon size={16} />
                    <span className="flex-1 truncate">{item.label}</span>
                  </NavLink>
                );
              })}
            </nav>
          </div>
        </div>
      </div>

      {/* Bottom Changelog / Release Widget (from Reference design) */}
      <div className="p-3 m-3 rounded-lg border border-[var(--border)] bg-[var(--surface)]">
        <div className="flex items-center justify-between mb-1">
          <span className="text-2xs font-semibold uppercase tracking-wider text-muted">TradeCraft v4.2</span>
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
        </div>
        <p className="text-xs font-medium text-text mb-1">Phase 4 Engine Active</p>
        <p className="text-2xs text-muted leading-tight mb-2">Deterministic diffing & content hash deduplication.</p>
        <div className="flex items-center text-2xs font-medium text-primary hover:underline cursor-pointer gap-1">
          <span>Release Notes</span>
          <ArrowUpRight size={11} />
        </div>
      </div>
    </aside>
  );
}
