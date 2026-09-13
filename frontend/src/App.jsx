import { Routes, Route, Navigate } from 'react-router-dom';
import AppLayout from './components/layout/AppLayout';
import ProtectedRoute from './components/auth/ProtectedRoute';
import PublicRoute from './components/auth/PublicRoute';
import Login from './pages/Login';
import Register from './pages/Register';
import Dashboard from './pages/Dashboard';
import Competitors from './pages/Competitors';
import Findings from './pages/Findings';
import Proposal from './pages/Proposal';

export default function App() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route element={<PublicRoute />}>
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
      </Route>

      {/* Protected Routes inside AppLayout */}
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/competitors" element={<Competitors />} />
          <Route path="/findings" element={<Findings />} />
          <Route path="/proposals" element={<Proposal />} />
          
          {/* Mock settings/help pages for the sidebar nav */}
          <Route path="/settings" element={<div className="p-12 text-center text-muted">Settings coming soon</div>} />
          <Route path="/help" element={<div className="p-12 text-center text-muted">Help & Support coming soon</div>} />
          
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Route>
      </Route>
      
      {/* Fallback for unmatched top-level routes */}
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}
