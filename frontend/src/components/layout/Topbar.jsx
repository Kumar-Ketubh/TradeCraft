import { useState, useRef, useEffect } from 'react';
import { useLocation, NavLink } from 'react-router-dom';
import { 
  LogOut, 
  Bell, 
  Moon, 
  Sun, 
  User, 
  Layers, 
  Plus, 
  Settings, 
  HelpCircle, 
  CheckCircle2, 
  Activity,
  ShieldCheck,
  ChevronDown
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import Modal from '../ui/Modal';
import Button from '../ui/Button';

const ROUTE_HEADERS = {
  '/dashboard': {
    title: 'Dashboard',
    subtitle: 'Welcome back to your dashboard'
  },
  '/competitors': {
    title: 'Competitors',
    subtitle: 'Manage monitored competitors and target sources'
  },
  '/findings': {
    title: 'Findings',
    subtitle: 'Detected changes & validated competitive movements'
  },
  '/proposals': {
    title: 'Proposals',
    subtitle: 'AI-generated tactical pitches & responses'
  },
  '/settings': {
    title: 'Settings',
    subtitle: 'Workspace preferences and account credentials'
  },
  '/help': {
    title: 'Help & Documentation',
    subtitle: 'Platform architecture and adapter guides'
  }
};

export default function Topbar({ isDark, setIsDark }) {
  const location = useLocation();
  const { currentUser, logout, workspaces, activeWorkspace, setActiveWorkspace, createWorkspace } = useAuth();
  
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newWsName, setNewWsName] = useState('');
  const [creating, setCreating] = useState(false);

  // Popover states for Notify and User profile
  const [showNotifications, setShowNotifications] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('open') === 'notifications';
  });
  const [showUserMenu, setShowUserMenu] = useState(() => {
    const params = new URLSearchParams(window.location.search);
    return params.get('open') === 'user';
  });
  const [unreadCount, setUnreadCount] = useState(2);

  const notifRef = useRef(null);
  const userMenuRef = useRef(null);

  const currentHeader = ROUTE_HEADERS[location.pathname] || {
    title: 'Dashboard',
    subtitle: 'Welcome back to your dashboard'
  };

  // Close popovers on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setShowNotifications(false);
      }
      if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
        setShowUserMenu(false);
      }
    }
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newWsName.trim()) return;
    setCreating(true);
    try {
      await createWorkspace(newWsName.trim());
      setNewWsName('');
      setShowCreateModal(false);
    } catch (err) {
      alert(err.message || 'Failed to create workspace');
    } finally {
      setCreating(false);
    }
  };

  const getUserInitials = (name) => {
    if (!name) return 'TC';
    const parts = name.trim().split(' ');
    if (parts.length >= 2) return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
    return name.slice(0, 2).toUpperCase();
  };

  const sampleNotifications = [
    {
      id: 1,
      title: 'Phase 4 Diff Engine Active',
      message: 'Deterministic content hashing & unified diff tracking initialized.',
      time: 'Just now',
      unread: true,
      icon: Activity,
      color: 'bg-emerald-500'
    },
    {
      id: 2,
      title: 'Workspace Scan Ready',
      message: `Monitored sources ready for capture in ${activeWorkspace?.name || 'Active Workspace'}.`,
      time: '10m ago',
      unread: true,
      icon: CheckCircle2,
      color: 'bg-blue-500'
    },
    {
      id: 3,
      title: 'Account Guard Active',
      message: 'Multi-tenant isolation verified with secure JWT authentication.',
      time: '1h ago',
      unread: false,
      icon: ShieldCheck,
      color: 'bg-purple-500'
    }
  ];

  return (
    <header className="topbar bg-surface border-b border-[var(--border)] flex items-center justify-between px-6 py-2.5 z-30">
      {/* Left: Dynamic Header Title & Workspace Selector */}
      <div className="flex items-center gap-6 flex-1 min-w-0">
        <div className="flex flex-col min-w-0">
          <h2 className="text-lg font-bold text-text tracking-tight truncate leading-tight">
            {currentHeader.title}
          </h2>
          <span className="text-xs text-muted truncate">
            {currentHeader.subtitle}
          </span>
        </div>

        {/* Workspace Selector Dropdown & New Workspace Trigger */}
        <div className="flex items-center gap-2 pl-4 border-l border-[var(--border)]">
          <Layers size={14} className="text-muted shrink-0" />
          <select
            className="text-xs font-medium py-1.5 px-2.5 rounded-lg border border-[var(--border)] bg-surface text-text cursor-pointer hover:border-primary transition-colors focus:outline-none"
            value={activeWorkspace ? activeWorkspace.id : ''}
            onChange={(e) => {
              const ws = workspaces.find((w) => w.id === e.target.value);
              if (ws) setActiveWorkspace(ws);
            }}
          >
            {workspaces.length === 0 && <option value="">No Workspaces</option>}
            {workspaces.map((ws) => (
              <option key={ws.id} value={ws.id}>
                {ws.name} ({ws.competitor_count || 0} competitors)
              </option>
            ))}
          </select>
          <button
            onClick={() => setShowCreateModal(true)}
            className="flex items-center gap-1 text-xs font-medium py-1.5 px-2.5 rounded-lg border border-dashed border-[var(--border)] text-muted hover:text-primary hover:border-primary transition-colors cursor-pointer bg-surface"
            title="Create New Workspace"
          >
            <Plus size={12} />
            <span>New</span>
          </button>
        </div>
      </div>

      {/* Right Controls: Exactly as in Reference Image: Notify, Dark Mode, User Profile/Logout */}
      <div className="flex items-center shrink-0" style={{ gap: '3px' }}>
        {/* 1. Notification Bell Button */}
        <div className="relative" ref={notifRef}>
          <button
            onClick={() => {
              setShowNotifications(!showNotifications);
              setShowUserMenu(false);
            }}
            className={`w-10 h-10 rounded-xl border flex items-center justify-center transition-all cursor-pointer relative shadow-xs ${
              showNotifications
                ? 'bg-[var(--surface-hover)] text-text border-primary'
                : 'bg-surface text-muted hover:text-text hover:bg-[var(--surface-hover)] border-[var(--border)] hover:border-gray-300 dark:hover:border-zinc-700'
            }`}
            title="Notifications"
            aria-label="View notifications"
          >
            <Bell size={18} />
            {unreadCount > 0 && (
              <span className="absolute top-2.5 right-2.5 w-2 h-2 rounded-full bg-red-500 ring-2 ring-white dark:ring-zinc-900"></span>
            )}
          </button>

          {/* Notification Dropdown Panel */}
          {showNotifications && (
            <div className="absolute right-0 top-full mt-2 w-80 rounded-2xl border border-[var(--border)] bg-surface shadow-xl z-50 overflow-hidden">
              <div className="px-4 py-3 border-b border-[var(--border)] flex items-center justify-between bg-[var(--surface-hover)]/40">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-text uppercase tracking-wider">Notifications</span>
                  {unreadCount > 0 && (
                    <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-red-500/10 text-red-500 border border-red-500/20">
                      {unreadCount} new
                    </span>
                  )}
                </div>
                {unreadCount > 0 && (
                  <button
                    onClick={() => setUnreadCount(0)}
                    className="text-2xs font-medium text-primary hover:underline cursor-pointer"
                  >
                    Mark all read
                  </button>
                )}
              </div>

              <div className="max-h-80 overflow-y-auto divide-y divide-[var(--border)]">
                {sampleNotifications.map((notif) => {
                  const Icon = notif.icon;
                  return (
                    <div 
                      key={notif.id} 
                      className="p-3.5 hover:bg-[var(--surface-hover)] transition-colors flex items-start gap-3 cursor-pointer"
                    >
                      <div className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${notif.color}`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center justify-between gap-2">
                          <p className="text-xs font-semibold text-text truncate">{notif.title}</p>
                          <span className="text-2xs text-muted shrink-0">{notif.time}</span>
                        </div>
                        <p className="text-2xs text-muted mt-0.5 leading-relaxed">{notif.message}</p>
                      </div>
                    </div>
                  );
                })}
              </div>

              <div className="p-2.5 border-t border-[var(--border)] bg-[var(--surface-hover)]/20 text-center">
                <span className="text-2xs text-muted font-medium">Real-time Competitive Intel Feed</span>
              </div>
            </div>
          )}
        </div>

        {/* 2. Dark Mode Toggle Button */}
        <button
          onClick={() => setIsDark(!isDark)}
          className="w-10 h-10 rounded-xl border border-[var(--border)] bg-surface text-muted hover:text-text hover:bg-[var(--surface-hover)] hover:border-gray-300 dark:hover:border-zinc-700 flex items-center justify-center transition-all cursor-pointer shadow-xs"
          title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
          aria-label="Toggle color theme"
        >
          {isDark ? (
            <Sun size={18} className="text-amber-400 transition-transform rotate-0 hover:rotate-45" />
          ) : (
            <Moon size={18} className="transition-transform hover:-rotate-12" />
          )}
        </button>

        {/* 3. User Profile & Logout Button (Matches reference user outline icon in rounded-xl square) */}
        <div className="relative" ref={userMenuRef}>
          <button
            onClick={() => {
              setShowUserMenu(!showUserMenu);
              setShowNotifications(false);
            }}
            className={`w-10 h-10 rounded-xl border flex items-center justify-center transition-all cursor-pointer shadow-xs ${
              showUserMenu
                ? 'bg-[var(--surface-hover)] text-text border-primary'
                : 'bg-surface text-muted hover:text-text hover:bg-[var(--surface-hover)] border-[var(--border)] hover:border-gray-300 dark:hover:border-zinc-700'
            }`}
            title="User Profile & Logout"
            aria-label="Account menu"
          >
            <User size={18} />
          </button>

          {/* User Profile & Logout Dropdown Menu */}
          {showUserMenu && (
            <div className="absolute right-0 top-full mt-2 w-64 rounded-2xl border border-[var(--border)] bg-surface shadow-xl z-50 overflow-hidden">
              {/* Profile Card Header */}
              <div className="p-4 border-b border-[var(--border)] bg-[var(--surface-hover)]/40">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl bg-blue-600/10 text-primary border border-blue-500/20 flex items-center justify-center font-bold text-sm shrink-0">
                    {getUserInitials(currentUser?.name || 'System Admin')}
                  </div>
                  <div className="flex flex-col min-w-0">
                    <span className="text-sm font-bold text-text truncate">
                      {currentUser?.name || 'System Admin'}
                    </span>
                    <span className="text-2xs text-muted truncate">
                      {currentUser?.email || 'admin@tradecraft.com'}
                    </span>
                  </div>
                </div>

                <div className="mt-3 pt-2 border-t border-[var(--border)] flex items-center justify-between">
                  <span className="text-2xs font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-500 border border-blue-500/20">
                    Pro Plan
                  </span>
                  <span className="text-2xs text-muted font-medium truncate max-w-[130px]" title={activeWorkspace?.name}>
                    {activeWorkspace?.name || 'Admin Workspace'}
                  </span>
                </div>
              </div>

              {/* Navigation Links */}
              <div className="p-1.5 flex flex-col gap-0.5">
                <NavLink
                  to="/settings"
                  onClick={() => setShowUserMenu(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium text-text hover:bg-[var(--surface-hover)] transition-colors"
                >
                  <Settings size={15} className="text-muted" />
                  <span>Account Settings</span>
                </NavLink>
                <NavLink
                  to="/help"
                  onClick={() => setShowUserMenu(false)}
                  className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium text-text hover:bg-[var(--surface-hover)] transition-colors"
                >
                  <HelpCircle size={15} className="text-muted" />
                  <span>Help & Documentation</span>
                </NavLink>
              </div>

              {/* Prominent Clean Log Out Action */}
              <div className="p-1.5 border-t border-[var(--border)] bg-[var(--surface-hover)]/20">
                <button
                  onClick={() => {
                    setShowUserMenu(false);
                    logout();
                  }}
                  className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-semibold text-danger hover:bg-red-500/10 transition-colors cursor-pointer text-left"
                >
                  <LogOut size={15} className="text-danger" />
                  <span>Log Out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Create Workspace Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create New Workspace"
      >
        <form onSubmit={handleCreate} className="space-y-4">
          <div className="form-group">
            <label className="block text-xs font-medium text-text mb-1">Workspace Name</label>
            <input
              type="text"
              placeholder="e.g. Enterprise Intelligence, Q4 Launch"
              value={newWsName}
              onChange={(e) => setNewWsName(e.target.value)}
              className="w-full text-sm py-2 px-3 rounded-lg border border-[var(--border)] bg-surface text-text focus:outline-none focus:border-primary"
              autoFocus
              required
            />
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              size="sm"
              onClick={() => setShowCreateModal(false)}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              size="sm"
              disabled={creating || !newWsName.trim()}
            >
              {creating ? 'Creating...' : 'Create Workspace'}
            </Button>
          </div>
        </form>
      </Modal>
    </header>
  );
}
