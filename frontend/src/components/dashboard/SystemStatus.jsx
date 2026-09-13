import Card from '../ui/Card';
import StatusBadge from '../ui/StatusBadge';

export default function SystemStatus({ healthStatus, healthError }) {
  return (
    <Card title="System Status" className="h-auto">
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
          <span className="text-sm font-semibold text-[var(--text)]">Frontend</span>
          <StatusBadge isRunning={true} status="Running" />
        </div>
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
          <span className="text-sm font-semibold text-[var(--text)]">Backend</span>
          <StatusBadge 
            isConnected={!healthError && healthStatus?.backend === 'ok'} 
            status={healthError ? 'Disconnected' : healthStatus ? 'Connected' : 'Checking...'} 
          />
        </div>
        <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
          <span className="text-sm font-semibold text-[var(--text)]">Database</span>
          <StatusBadge 
            isConnected={healthStatus?.database === 'ok'} 
            status={healthError ? 'Error' : healthStatus?.database === 'ok' ? 'Connected' : 'Config Pending'} 
          />
        </div>
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold text-[var(--text)]">AI Workflow</span>
          <StatusBadge status="Not Connected" />
        </div>
      </div>
    </Card>
  );
}
