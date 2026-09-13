import { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

export default function AppLayout() {
  const [isDark, setIsDark] = useState(false);

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }, [isDark]);

  return (
    <div className={`app-layout ${isDark ? 'dark' : ''}`}>
      <Sidebar />
      <div className="main-wrapper">
        <Topbar isDark={isDark} setIsDark={setIsDark} />
        <main className="main-content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
