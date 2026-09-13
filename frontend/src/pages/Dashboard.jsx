import { useState, useEffect } from 'react';
import MetricCard from '../components/dashboard/MetricCard';
import SystemStatus from '../components/dashboard/SystemStatus';
import RecentFindings from '../components/dashboard/RecentFindings';
import CompetitorOverview from '../components/dashboard/CompetitorOverview';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Building2, Link, Activity, Search } from 'lucide-react';

export default function Dashboard() {
  const { activeWorkspace } = useAuth();
  const [healthStatus, setHealthStatus] = useState(null);
  const [healthError, setHealthError] = useState(null);

  const [workspaceStats, setWorkspaceStats] = useState({
    competitorCount: 0,
    sourceCount: 0,
    activeMonitoringCount: 0,
  });

  useEffect(() => {
    checkBackendHealth();
    const interval = setInterval(checkBackendHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    if (activeWorkspace) {
      loadWorkspaceMetrics();
    } else {
      setWorkspaceStats({
        competitorCount: 0,
        sourceCount: 0,
        activeMonitoringCount: 0,
      });
    }
  }, [activeWorkspace?.id]);

  const checkBackendHealth = async () => {
    try {
      const data = await api.checkHealth();
      setHealthStatus(data);
      setHealthError(null);
    } catch (err) {
      setHealthError(err.message || 'Backend unreachable');
      setHealthStatus(null);
    }
  };

  const loadWorkspaceMetrics = async () => {
    if (!activeWorkspace) return;
    try {
      const compList = await api.competitors.list(activeWorkspace.id);
      let totalSources = 0;
      let activeMonitoring = 0;

      compList.forEach((c) => {
        totalSources += c.source_count || 0;
        if (c.monitoring_enabled) activeMonitoring++;
      });

      setWorkspaceStats({
        competitorCount: compList.length,
        sourceCount: totalSources,
        activeMonitoringCount: activeMonitoring,
      });
    } catch (err) {
      console.warn('Could not load workspace metrics:', err);
    }
  };

  return (
    <div>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <MetricCard
          title="Competitors Monitored"
          value={workspaceStats.competitorCount}
          description="Active competitors"
          icon={Building2}
          colorClass="blue"
        />
        <MetricCard
          title="Sources Configured"
          value={workspaceStats.sourceCount}
          description="Across monitored competitors"
          icon={Link}
          colorClass="green"
        />
        <MetricCard
          title="Latest Scan"
          value="Not run yet"
          description="Monitoring not implemented"
          icon={Activity}
          colorClass="purple"
        />
        <MetricCard
          title="Findings"
          value="0"
          description="No validated findings yet"
          icon={Search}
          colorClass="orange"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="lg:col-span-2">
          <RecentFindings />
        </div>
        <div className="space-y-6">
          <SystemStatus healthStatus={healthStatus} healthError={healthError} />
          <CompetitorOverview workspaceStats={workspaceStats} />
        </div>
      </div>
    </div>
  );
}
