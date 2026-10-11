// frontend/src/pages/Dashboard.jsx
// Minimalist, spacious Dashboard layout with clean typography, generous padding, and clear table layout

import { useState, useEffect, useCallback } from 'react';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { 
  Building2, 
  Link, 
  Activity, 
  Search, 
  Play, 
  RefreshCw, 
  TrendingUp,
  ArrowUpRight,
  CheckCircle2, 
  AlertCircle,
  Clock,
  Sparkles,
  ShieldCheck
} from 'lucide-react';
import { NavLink } from 'react-router-dom';

export default function Dashboard() {
  const { activeWorkspace } = useAuth();
  const [healthStatus, setHealthStatus] = useState(null);

  const [workspaceStats, setWorkspaceStats] = useState({
    competitorCount: 0,
    sourceCount: 0,
    activeMonitoringCount: 0,
  });

  const [scansList, setScansList] = useState([]);
  const [latestScan, setLatestScan] = useState(null);
  const [recentChanges, setRecentChanges] = useState([]);
  const [scanning, setScanning] = useState(false);
  const [scanMessage, setScanMessage] = useState(null);

  const checkBackendHealth = useCallback(async () => {
    try {
      const data = await api.checkHealth();
      setHealthStatus(data);
    } catch {
      setHealthStatus(null);
    }
  }, []);

  const loadWorkspaceMetrics = useCallback(async () => {
    if (!activeWorkspace?.id) return;
    try {
      const compList = await api.competitors.list(activeWorkspace.id);
      let totalSources = 0;
      let activeMonitoring = 0;

      (compList || []).forEach((c) => {
        totalSources += c.source_count || 0;
        if (c.monitoring_enabled) activeMonitoring++;
      });

      setWorkspaceStats({
        competitorCount: (compList || []).length,
        sourceCount: totalSources,
        activeMonitoringCount: activeMonitoring,
      });
    } catch (err) {
      console.warn('Could not load workspace metrics:', err);
    }
  }, [activeWorkspace]);

  const loadWorkspaceScans = useCallback(async () => {
    if (!activeWorkspace?.id) {
      setScansList([]);
      setLatestScan(null);
      return;
    }
    try {
      const data = await api.scans.listWorkspaceScans(activeWorkspace.id);
      const list = Array.isArray(data) ? data : [];
      setScansList(list);
      setLatestScan(list.length > 0 ? list[0] : null);
    } catch (err) {
      console.warn('Could not load workspace scans:', err);
    }
  }, [activeWorkspace]);

  const loadRecentChanges = useCallback(async () => {
    if (!activeWorkspace?.id) return;
    try {
      const data = await api.changes.listByWorkspace(activeWorkspace.id, { limit: 5 });
      setRecentChanges(Array.isArray(data) ? data : []);
    } catch (err) {
      console.warn('Could not load recent changes:', err);
    }
  }, [activeWorkspace]);

  useEffect(() => {
    checkBackendHealth();
  }, [checkBackendHealth]);

  useEffect(() => {
    if (activeWorkspace?.id) {
      loadWorkspaceMetrics();
      loadWorkspaceScans();
      loadRecentChanges();
    }
  }, [activeWorkspace, loadWorkspaceMetrics, loadWorkspaceScans, loadRecentChanges]);

  const handleRunScan = async () => {
    if (!activeWorkspace?.id || scanning) return;
    setScanning(true);
    setScanMessage(null);
    try {
      const result = await api.scans.triggerWorkspaceScan(activeWorkspace.id);
      if (result.total_sources === 0) {
        setScanMessage({
          type: 'info',
          text: 'Scan completed: No active monitored sources found in this workspace. Add competitors and sources to begin monitoring.',
        });
      } else if (result.status === 'failed') {
        setScanMessage({
          type: 'error',
          text: `Scan failed: All ${result.total_sources} sources failed to fetch. ${result.error_message || ''}`.trim(),
        });
      } else if (result.status === 'partial') {
        setScanMessage({
          type: 'warning',
          text: `Scan partial: ${result.successful_sources}/${result.total_sources} sources captured (${result.failed_sources} failed).`,
        });
      } else {
        setScanMessage({
          type: 'success',
          text: `Scan completed: ${result.successful_sources}/${result.total_sources} sources captured successfully.`,
        });
      }
      await Promise.all([loadWorkspaceMetrics(), loadWorkspaceScans(), loadRecentChanges()]);
    } catch (err) {
      setScanMessage({
        type: 'error',
        text: err.message || 'Failed to trigger workspace scan',
      });
    } finally {
      setScanning(false);
    }
  };

  const formatScanTime = (isoString) => {
    if (!isoString) return 'Not run yet';
    try {
      const date = new Date(isoString);
      const now = new Date();
      const diffSec = Math.floor((now - date) / 1000);
      if (diffSec < 60) return 'Just now';
      if (diffSec < 3600) return `${Math.floor(diffSec / 60)}m ago`;
      if (diffSec < 86400) return `${Math.floor(diffSec / 3600)}h ago`;
      return `${Math.floor(diffSec / 86400)}d ago`;
    } catch {
      return '';
    }
  };

  return (
    <div className="space-y-8 max-w-7xl mx-auto pb-12">
      {/* Top Banner Row */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-2">
        <div>
          <h2 className="text-xl font-bold text-text tracking-tight">Competitive Intelligence Overview</h2>
          <p className="text-xs text-muted mt-1">
            Active workspace: <strong className="text-text font-semibold">{activeWorkspace?.name || 'Default Workspace'}</strong>
          </p>
        </div>

        <Button
          variant="primary"
          size="md"
          onClick={handleRunScan}
          disabled={scanning || !activeWorkspace}
          className="rounded-xl px-5 py-2.5 shrink-0"
        >
          {scanning ? (
            <>
              <RefreshCw size={14} className="spin mr-2" style={{ animation: 'spin 1s linear infinite' }} />
              <span>Scanning All Targets...</span>
            </>
          ) : (
            <>
              <Play size={14} className="mr-2" />
              <span>Run Workspace Scan</span>
            </>
          )}
        </Button>
      </div>

      {/* Feedback banner */}
      {scanMessage && (
        <div className={`p-4 text-xs rounded-xl border flex items-center justify-between ${
          scanMessage.type === 'success' 
            ? 'bg-success-light text-success border-[var(--border)]' 
            : scanMessage.type === 'warning'
            ? 'bg-warning-light text-warning border-[var(--border)]'
            : scanMessage.type === 'info'
            ? 'bg-primary-light text-primary border-[var(--border)]'
            : 'alert-banner alert-error'
        }`}>
          <div className="flex items-center gap-2.5">
            {scanMessage.type === 'success' && <CheckCircle2 size={16} />}
            {scanMessage.type === 'warning' && <AlertCircle size={16} />}
            {scanMessage.type === 'info' && <AlertCircle size={16} />}
            {scanMessage.type === 'error' && <AlertCircle size={16} />}
            <span className="font-medium">{scanMessage.text}</span>
          </div>
          <button onClick={() => setScanMessage(null)} className="font-bold text-sm hover:opacity-75 cursor-pointer">×</button>
        </div>
      )}

      {/* Row 1: 4 Spacious Metric Cards (Minimalist first iteration design) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        <div className="card p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-muted">Competitors Monitored</span>
            <div className="p-2 rounded-lg bg-primary-light text-primary">
              <Building2 size={16} />
            </div>
          </div>
          <div className="text-3xl font-bold text-text tracking-tight mb-2">
            {workspaceStats.competitorCount}
          </div>
          <div className="text-xs text-success font-medium flex items-center gap-1">
            <TrendingUp size={12} />
            <span>Active targets</span>
          </div>
        </div>

        <div className="card p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-muted">Sources Monitored</span>
            <div className="p-2 rounded-lg bg-success-light text-success">
              <Link size={16} />
            </div>
          </div>
          <div className="text-3xl font-bold text-text tracking-tight mb-2">
            {workspaceStats.sourceCount}
          </div>
          <div className="text-xs text-muted">
            {workspaceStats.activeMonitoringCount} active polling
          </div>
        </div>

        <div className="card p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-muted">Latest Scan Run</span>
            <div className="p-2 rounded-lg bg-purple-light text-purple">
              <Activity size={16} />
            </div>
          </div>
          <div className="text-3xl font-bold text-text tracking-tight mb-2">
            {latestScan ? latestScan.status.toUpperCase() : 'NO RUNS'}
          </div>
          <div className="text-xs text-muted flex items-center gap-1">
            <Clock size={12} />
            <span>{formatScanTime(latestScan?.created_at)}</span>
          </div>
        </div>

        <div className="card p-6 flex flex-col justify-between">
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-medium text-muted">Detected Findings</span>
            <div className="p-2 rounded-lg bg-warning-light text-warning">
              <Sparkles size={16} />
            </div>
          </div>
          <div className="text-3xl font-bold text-text tracking-tight mb-2">
            {recentChanges.length}
          </div>
          <div className="text-xs text-primary font-medium flex items-center gap-1">
            <NavLink to="/findings" className="hover:underline flex items-center gap-1">
              <span>View findings</span>
              <ArrowUpRight size={12} />
            </NavLink>
          </div>
        </div>
      </div>

      {/* Row 2: Spacious Scans Section & Recent Findings (2 Columns, generous padding) */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Scans Table (60%) */}
        <div className="card p-6 lg:col-span-3 flex flex-col">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h3 className="text-base font-semibold text-text tracking-tight">Recent Scan Runs</h3>
              <p className="text-xs text-muted mt-0.5">Execution logs for monitored URLs</p>
            </div>
            <span className="text-xs text-muted font-medium bg-[var(--bg)] px-2.5 py-1 rounded-md border border-[var(--border)]">
              {scansList.length} scans recorded
            </span>
          </div>

          {scansList.length === 0 ? (
            <div className="p-12 text-center text-muted text-xs border border-[var(--border)] border-dashed rounded-lg">
              No scans recorded yet. Click "Run Workspace Scan" above to initiate a scan.
            </div>
          ) : (
            <div className="table-wrapper">
              <table className="table">
                <thead>
                  <tr>
                    <th style={{ padding: '12px 16px' }}>Scan ID</th>
                    <th style={{ padding: '12px 16px' }}>Executed</th>
                    <th style={{ padding: '12px 16px' }}>Status</th>
                    <th style={{ padding: '12px 16px' }}>Captured</th>
                  </tr>
                </thead>
                <tbody>
                  {scansList.slice(0, 5).map((scan) => (
                    <tr key={scan.id}>
                      <td style={{ padding: '14px 16px' }} className="font-mono text-xs text-muted">
                        {scan.id.substring(0, 8)}...
                      </td>
                      <td style={{ padding: '14px 16px' }} className="text-xs text-muted font-medium">
                        {formatScanTime(scan.created_at)}
                      </td>
                      <td style={{ padding: '14px 16px' }}>
                        <Badge variant={scan.status === 'completed' ? 'success' : 'danger'}>
                          {scan.status}
                        </Badge>
                      </td>
                      <td style={{ padding: '14px 16px' }} className="text-xs font-semibold text-text">
                        {scan.successful_sources || 0} / {scan.total_sources || 0} sources
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Recent Activity / Findings (40%) */}
        <div className="card p-6 lg:col-span-2 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between mb-6">
              <div>
                <h3 className="text-base font-semibold text-text tracking-tight">Recent Intelligence</h3>
                <p className="text-xs text-muted mt-0.5">Verified competitor movements</p>
              </div>
              <NavLink to="/findings" className="text-xs text-primary font-medium hover:underline flex items-center gap-1">
                <span>View all</span>
                <ArrowUpRight size={13} />
              </NavLink>
            </div>

            <div className="space-y-4">
              {recentChanges.length === 0 ? (
                <div className="p-8 text-center text-muted text-xs border border-[var(--border)] border-dashed rounded-lg">
                  No competitor changes detected yet.
                </div>
              ) : (
                recentChanges.map((ch) => (
                  <div key={ch.id} className="p-4 rounded-lg border border-[var(--border)] bg-[var(--bg)] flex flex-col gap-2">
                    <div className="flex items-center justify-between text-xs">
                      <span className="font-bold text-text">{ch.competitor_name}</span>
                      <Badge variant={ch.category === 'pricing_change' ? 'danger' : 'primary'}>
                        {ch.category === 'pricing_change' ? 'Pricing Shift' : 'Feature Launch'}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted leading-relaxed font-normal">
                      {ch.summary}
                    </p>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="pt-4 border-t border-[var(--border)] flex items-center justify-between text-2xs text-muted mt-6">
            <div className="flex items-center gap-1.5">
              <ShieldCheck size={14} className="text-emerald-500" />
              <span>Multi-tenant data isolation active</span>
            </div>
            <span>TradeCraft Engine</span>
          </div>
        </div>
      </div>
    </div>
  );
}
