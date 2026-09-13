import PageHeader from '../components/ui/PageHeader';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';

export default function Proposal() {
  return (
    <div>
      <PageHeader 
        title="Proposals" 
        description="Turn validated findings into actionable project proposals."
      />

      <Card title="Proposal Generation" className="max-w-2xl mx-auto">
        <div className="flex flex-col items-center gap-3 mb-8 mt-4">
          <div className="text-sm font-semibold bg-[var(--bg)] px-6 py-3 border border-[var(--border)] rounded-md w-64 text-center">Validated Finding</div>
          <div className="text-muted">↓</div>
          <div className="text-sm font-semibold bg-[var(--bg)] px-6 py-3 border border-[var(--border)] rounded-md w-64 text-center">Evidence</div>
          <div className="text-muted">↓</div>
          <div className="text-sm font-semibold bg-[var(--bg)] px-6 py-3 border border-[var(--border)] rounded-md w-64 text-center">Analysis</div>
          <div className="text-muted">↓</div>
          <div className="text-sm font-semibold bg-[var(--primary-bg)] px-6 py-3 border border-[var(--primary)] rounded-md w-64 text-center text-[var(--primary)] shadow-sm">Project Proposal</div>
        </div>

        <div className="text-center p-6 bg-[var(--bg)] rounded-md border border-[var(--border)] border-dashed">
          <p className="text-sm mb-4 text-[var(--text)] font-medium">
            Proposal generation is currently unavailable.
          </p>
          <p className="text-sm text-muted mb-6">
            It will be enabled once the TradeCraft intelligence workflow is implemented.
          </p>
          <Button variant="disabled" disabled>
            Generate Proposal
          </Button>
        </div>
      </Card>
    </div>
  );
}
