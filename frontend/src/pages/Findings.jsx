import PageHeader from '../components/ui/PageHeader';

export default function Findings() {
  return (
    <div>
      <PageHeader 
        title="Findings" 
        description="Review validated competitive intelligence."
      />

      <div className="flex flex-col items-center justify-center p-12 text-center text-muted border border-[var(--border)] border-dashed rounded-md bg-[var(--bg)] min-h-[300px]">
        <h3 className="text-lg font-semibold text-text mb-2">No validated findings yet.</h3>
        <p className="max-w-md mx-auto">
          Once TradeCraft's monitoring and analysis workflow is implemented, validated competitor intelligence will appear here.
        </p>
      </div>
    </div>
  );
}
