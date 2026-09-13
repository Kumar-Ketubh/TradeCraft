import Card from '../ui/Card';
import { Building2, Link, Activity, Search } from 'lucide-react';

export default function CompetitorOverview({ workspaceStats }) {
  // In a real application, this would map over the actual competitors array
  // For now, we will display a professional empty/summary state based on stats
  return (
    <Card title="Competitor Overview" className="h-full">
      <div className="flex flex-col gap-4">
        {workspaceStats.competitorCount > 0 ? (
          <>
            <div className="flex items-center justify-between p-3 border border-[var(--border)] rounded-md bg-[var(--bg)]">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-[var(--primary-bg)] text-[var(--primary)] rounded">
                  <Building2 size={16} />
                </div>
                <div>
                  <div className="text-sm font-semibold text-[var(--text)]">Total Monitored</div>
                  <div className="text-xs text-muted">{workspaceStats.competitorCount} competitors</div>
                </div>
              </div>
            </div>
            
            <div className="flex items-center justify-between p-3 border border-[var(--border)] rounded-md bg-[var(--bg)]">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-[var(--primary-bg)] text-[var(--primary)] rounded">
                  <Link size={16} />
                </div>
                <div>
                  <div className="text-sm font-semibold text-[var(--text)]">Total Sources</div>
                  <div className="text-xs text-muted">{workspaceStats.sourceCount} specific URLs</div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="text-center py-6 text-muted border border-[var(--border)] rounded-md border-dashed">
            <p className="text-sm">No competitors added yet.</p>
          </div>
        )}
      </div>
    </Card>
  );
}
