import Card from '../ui/Card';

export default function RecentFindings() {
  return (
    <Card title="Recent Findings" className="h-full">
      <div className="flex flex-col items-center justify-center p-12 text-center text-muted border border-[var(--border)] border-dashed rounded-md bg-[var(--bg)] h-64">
        <h3 className="text-lg font-semibold text-text mb-2">No findings yet</h3>
        <p className="text-sm max-w-sm mb-4">
          TradeCraft will display validated competitor changes here once source monitoring, change detection, analysis and verification are implemented.
        </p>
      </div>
    </Card>
  );
}
