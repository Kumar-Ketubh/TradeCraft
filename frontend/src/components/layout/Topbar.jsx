import { LogOut, Bell, Moon, Sun, User } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';

export default function Topbar({ isDark, setIsDark }) {
  const { logout } = useAuth();

  return (
    <header className="topbar bg-surface border-b">
      <div className="flex items-center flex-1">
        <div className="flex-col">
          <h2 className="text-xl font-bold text-text">Dashboard</h2>
          <span className="text-sm text-muted">Competitive intelligence overview</span>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="relative p-2 rounded-lg bg-surface border text-muted hover:bg-bg hover:text-text transition-colors">
          <Bell className="h-5 w-5" />
          <span className="absolute -top-1 -right-1 h-3 w-3 bg-red-500 rounded-full border-2"></span>
        </button>
        <button
          onClick={() => setIsDark(!isDark)}
          className="flex h-10 w-10 items-center justify-center rounded-lg border bg-surface text-muted hover:bg-bg hover:text-text transition-colors"
        >
          {isDark ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </button>
        <button className="p-2 rounded-lg bg-surface border text-muted hover:bg-bg hover:text-text transition-colors">
          <User className="h-5 w-5" />
        </button>
        <button 
          onClick={logout}
          className="p-2 text-muted hover:text-danger transition-colors ml-2"
          title="Log Out"
        >
          <LogOut size={18} />
        </button>
      </div>
    </header>
  );
}
