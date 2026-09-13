import Card from '../ui/Card';
import { Activity } from 'lucide-react';

export default function MetricCard({ title, value, description, icon: Icon, colorClass = "blue" }) {
  // Use our raw CSS utility classes
  const colorMap = {
    blue: { bg: 'bg-primary-light', text: 'text-primary' },
    green: { bg: 'bg-success-light', text: 'text-success' },
    orange: { bg: 'bg-warning-light', text: 'text-warning' },
    purple: { bg: 'bg-purple-light', text: 'text-purple' },
  };

  const selectedColor = colorMap[colorClass] || colorMap.blue;

  return (
    <Card className="flex flex-col h-full border p-6 hover:shadow-md transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <div className={`p-2 rounded-lg ${selectedColor.bg}`}>
          {Icon && <Icon className={`h-5 w-5 ${selectedColor.text}`} />}
        </div>
        <Activity className="h-4 w-4 text-success" />
      </div>
      <h3 className="font-medium text-muted mb-1">{title}</h3>
      <p className="text-2xl font-bold text-text">{value}</p>
      <p className="text-sm text-muted mt-1">{description}</p>
    </Card>
  );
}
