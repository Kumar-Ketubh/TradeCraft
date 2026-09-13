import Card from '../ui/Card';
import Button from '../ui/Button';
import StatusBadge from '../ui/StatusBadge';
import { Edit2, Trash2 } from 'lucide-react';

export default function CompetitorCard({ competitor, onEdit, onDelete, onToggleMonitoring, onConfigureSources }) {
  return (
    <Card className="flex flex-col h-full">
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-bold text-lg leading-tight">{competitor.name}</h3>
        <button 
          className={`badge-btn ${competitor.monitoring_enabled ? 'badge-active' : 'badge-inactive'}`}
          onClick={() => onToggleMonitoring(competitor)}
        >
          {competitor.monitoring_enabled ? 'Monitoring Enabled' : 'Monitoring Disabled'}
        </button>
      </div>

      <div className="text-sm text-muted mb-4">
        {competitor.website && (
          <a href={competitor.website} target="_blank" rel="noreferrer" className="hover:underline">
            {competitor.website}
          </a>
        )}
      </div>

      <div className="mt-auto pt-4 border-t border-[var(--border)] flex justify-between items-center">
        <div className="flex items-center gap-4 text-sm">
          <span className="font-medium">Sources: {competitor.source_count || 0}</span>
          <Button variant="ghost" size="sm" onClick={() => onConfigureSources(competitor)}>
            Configure Sources
          </Button>
        </div>
        <div className="flex gap-2">
          <Button variant="secondary" size="sm" onClick={() => onEdit(competitor)} title="Edit">
            <Edit2 size={16} />
          </Button>
          <Button variant="danger" size="sm" onClick={() => onDelete(competitor.id)} title="Delete">
            <Trash2 size={16} />
          </Button>
        </div>
      </div>
    </Card>
  );
}
