// frontend/src/components/dashboard/RecentFindings.jsx
// Displays real-time verified intelligence findings from the LangGraph agent pipeline

import { useState, useEffect } from 'react';
import Card from '../ui/Card';
import Badge from '../ui/Badge';
import { api } from '../../services/api';
import { useAuth } from '../../context/AuthContext';
import { Sparkles, ShieldCheck, ArrowRight, FileText } from 'lucide-react';
import { Link } from 'react-router-dom';

export default function RecentFindings() {
  const { activeWorkspace } = useAuth();
  const [findings, setFindings] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    async function loadFindings() {
      if (!activeWorkspace?.id) return;
      setLoading(true);
      try {
        const data = await api.findings.listByWorkspace(activeWorkspace.id, { limit: 5 });
        setFindings(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error('Failed to load recent findings:', err);
      } finally {
        setLoading(false);
      }
    }
    loadFindings();
  }, [activeWorkspace?.id]);

  return (
    <Card
      title="Recent Intelligence Findings"
      action={
        <Link to="/findings" className="text-xs text-[var(--primary)] hover:underline flex items-center gap-1 font-medium">
          <span>All Findings</span>
          <ArrowRight size={12} />
        </Link>
      }
      className="h-full"
    >
      {loading ? (
        <div className="flex flex-col items-center justify-center p-12 text-muted h-64 gap-2">
          <div className="w-6 h-6 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
          <span className="text-xs">Loading verified findings...</span>
        </div>
      ) : findings.length === 0 ? (
        <div className="flex flex-col items-center justify-center p-8 text-center text-muted border border-[var(--border)] border-dashed rounded-md bg-[var(--bg)] h-64">
          <Sparkles size={28} className="text-muted mb-2 opacity-40" />
          <h3 className="text-sm font-semibold text-text mb-1">No findings yet</h3>
          <p className="text-xs max-w-sm mb-3">
            TradeCraft generates evidence-grounded findings automatically when competitor scans detect meaningful changes.
          </p>
          <Link to="/competitors" className="btn btn-secondary btn-xs">
            Trigger Scan
          </Link>
        </div>
      ) : (
        <div className="divide-y divide-[var(--border)]">
          {findings.map((f) => {
            const dateStr = f.created_at
              ? new Date(f.created_at).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                })
              : '';

            return (
              <div key={f.id} className="py-3.5 first:pt-1 last:pb-1 flex flex-col gap-1.5 hover:bg-[var(--bg)]/50 px-2 rounded transition-colors">
                <div className="flex items-center justify-between gap-2">
                  <span className="text-xs font-semibold text-text truncate max-w-md">
                    {f.title}
                  </span>
                  <span className="text-2xs text-muted whitespace-nowrap">{dateStr}</span>
                </div>

                <p className="text-xs text-muted line-clamp-2 leading-relaxed">
                  {f.factual_summary}
                </p>

                <div className="flex items-center gap-2 pt-1">
                  <Badge variant={f.verification_status === 'VERIFIED' ? 'success' : 'warning'}>
                    <ShieldCheck size={10} className="mr-1 inline" />
                    {f.grounding_score}% EGA
                  </Badge>
                  <Badge variant="purple">{f.category}</Badge>
                  {f.evidence_quotes && f.evidence_quotes.length > 0 && (
                    <span className="text-2xs text-muted flex items-center gap-0.5">
                      <FileText size={11} />
                      {f.evidence_quotes.length} quote{f.evidence_quotes.length > 1 ? 's' : ''}
                    </span>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
