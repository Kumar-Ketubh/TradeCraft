// frontend/src/components/changes/ChangeCard.jsx
// Clean, spacious, minimal card design with breathing room and clear typography

import { useState } from 'react';
import Badge from '../ui/Badge';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import DiffViewer from './DiffViewer';
import { api } from '../../services/api';
import { ExternalLink, GitCompare, ArrowUpRight } from 'lucide-react';

const CATEGORY_MAP = {
  pricing_change: { variant: 'danger', label: 'Pricing Shift' },
  feature_announcement: { variant: 'primary', label: 'Feature Launch' },
  documentation_update: { variant: 'neutral', label: 'Documentation' },
  blog_post: { variant: 'purple', label: 'Blog & News' },
  positioning_shift: { variant: 'warning', label: 'Positioning' },
  noise: { variant: 'neutral', label: 'Noise' },
  unknown: { variant: 'neutral', label: 'Content Update' },
};

export default function ChangeCard({ change }) {
  const [showDiff, setShowDiff] = useState(false);
  const [diffDetail, setDiffDetail] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleViewDiff = async () => {
    setShowDiff(true);
    if (!diffDetail) {
      setLoading(true);
      try {
        const detail = await api.changes.getById(change.id);
        setDiffDetail(detail);
      } catch (e) {
        console.error('Failed to load diff:', e);
      } finally {
        setLoading(false);
      }
    }
  };

  const stats = change.diff_stats || {};
  const meta = CATEGORY_MAP[change.category] || CATEGORY_MAP.unknown;
  const detectedAt = change.detected_at
    ? new Date(change.detected_at).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      })
    : 'Recently';

  const impactPct = Math.round((change.significance_score || 0) * 100);

  return (
    <>
      <div className="card p-6 flex flex-col gap-5 hover:shadow-md transition-shadow">
        {/* Top Header Row with spacious layout */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div className="flex items-center gap-3 flex-wrap">
            <h3 className="text-base font-bold text-text tracking-tight m-0">
              {change.competitor_name || 'Competitor'}
            </h3>
            <Badge variant={change.is_meaningful ? meta.variant : 'neutral'}>
              {meta.label}
            </Badge>
            {change.source_url && (
              <a
                href={change.source_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-muted hover:text-primary transition-colors inline-flex items-center gap-1 max-w-sm truncate"
              >
                <ExternalLink size={12} className="shrink-0" />
                <span className="truncate">{change.source_name || change.source_url}</span>
              </a>
            )}
          </div>

          <span className="text-xs text-muted font-medium whitespace-nowrap">
            {detectedAt}
          </span>
        </div>

        {/* Spacious Summary Content Box */}
        {change.summary && (
          <div className="p-4 rounded-lg bg-[var(--bg)] border border-[var(--border)] text-sm text-text leading-relaxed font-normal">
            {change.summary}
          </div>
        )}

        {/* Bottom Metadata & Actions Bar */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-3 border-t border-[var(--border)]">
          {/* Diff Metrics */}
          <div className="flex items-center gap-5 text-xs text-muted flex-wrap">
            <div className="flex items-center gap-2">
              <span className="font-medium">Impact:</span>
              <strong className="text-text font-semibold">{impactPct}%</strong>
            </div>

            {stats.lines_added !== undefined && (
              <span className="font-medium text-success">
                +{stats.lines_added} lines
              </span>
            )}

            {stats.lines_removed !== undefined && (
              <span className="font-medium text-danger">
                -{stats.lines_removed} lines
              </span>
            )}

            {stats.similarity_ratio !== undefined && (
              <span>
                {Math.round(stats.similarity_ratio * 100)}% match
              </span>
            )}
          </div>

          {/* Action Trigger */}
          <Button
            variant="secondary"
            size="sm"
            onClick={handleViewDiff}
            className="self-start sm:self-auto"
          >
            <GitCompare size={13} className="mr-1.5" />
            <span>View Diff</span>
          </Button>
        </div>
      </div>

      {/* Diff Inspection Modal */}
      <Modal
        isOpen={showDiff}
        onClose={() => setShowDiff(false)}
        title={`Diff Inspection — ${change.competitor_name || 'Change'}`}
      >
        {loading ? (
          <div className="p-12 text-center text-muted text-sm flex flex-col items-center justify-center gap-3">
            <div className="w-6 h-6 border-2 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
            <span>Loading unified diff...</span>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between text-xs text-muted pb-2 border-b border-[var(--border)]">
              <span>Line-by-line snapshot comparison</span>
              <span className="font-mono text-2xs bg-[var(--bg)] px-2 py-0.5 rounded border border-[var(--border)]">
                Hash: {change.change_hash?.slice(0, 16)}...
              </span>
            </div>
            <DiffViewer diffUnified={diffDetail?.diff_unified || ''} />
          </div>
        )}
      </Modal>
    </>
  );
}
