import { useState, useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import Topbar from './Topbar';

export default function AppLayout() {
  const [isDark, setIsDark] = useState(() => {
    const urlParams = new URLSearchParams(window.location.search);
    const themeParam = urlParams.get('theme');
    if (themeParam) return themeParam === 'dark';
    return localStorage.getItem('tradecraft_theme') === 'dark';
  });

  useEffect(() => {
    if (isDark) {
      document.documentElement.classList.add('dark');
      localStorage.setItem('tradecraft_theme', 'dark');
    } else {
      document.documentElement.classList.remove('dark');
      localStorage.setItem('tradecraft_theme', 'light');
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
