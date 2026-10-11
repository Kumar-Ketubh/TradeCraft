// frontend/src/pages/Findings.jsx
// Minimalist, spacious Findings feed with clear margins, filters, and breathing room

import { useState, useEffect, useCallback } from 'react';
import PageHeader from '../components/ui/PageHeader';
import ChangeCard from '../components/changes/ChangeCard';
import Button from '../components/ui/Button';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { Filter, RefreshCw, AlertCircle, Sparkles, Inbox } from 'lucide-react';

const CATEGORIES = [
  { value: '', label: 'All Categories' },
  { value: 'pricing_change', label: 'Pricing Shifts' },
  { value: 'feature_announcement', label: 'Feature Launches' },
  { value: 'documentation_update', label: 'Documentation' },
  { value: 'blog_post', label: 'Blog & News' },
  { value: 'positioning_shift', label: 'Positioning' },
];

export default function Findings() {
  const { activeWorkspace } = useAuth();
  const [changes, setChanges] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [meaningfulOnly, setMeaningfulOnly] = useState(false);
  const [category, setCategory] = useState('');

  const loadChanges = useCallback(async () => {
    if (!activeWorkspace?.id) return;
    setLoading(true);
    setError(null);
    try {
      const params = { limit: 100 };
      if (meaningfulOnly) params.is_meaningful = true;
      if (category) params.category = category;
      const data = await api.changes.listByWorkspace(activeWorkspace.id, params);
      setChanges(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message || 'Failed to load changes');
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace?.id, meaningfulOnly, category]);

  useEffect(() => {
    loadChanges();
  }, [loadChanges]);

  const meaningfulCount = changes.filter((c) => c.is_meaningful).length;

  return (
    <div className="space-y-8 max-w-5xl mx-auto pb-12">
      <PageHeader
        title="Findings"
        description="Review detected competitor movements, pricing changes, and feature updates."
      />

      {/* Filter and Control Toolbar with generous padding */}
      <div className="card p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-1.5 text-xs text-muted font-medium mr-1">
            <Filter size={14} />
            <span>Filters:</span>
          </div>

          <button
            onClick={() => setMeaningfulOnly((v) => !v)}
            className={`btn btn-sm ${meaningfulOnly ? 'btn-primary' : 'btn-secondary'}`}
          >
            <Sparkles size={13} className="mr-1" />
            <span>Meaningful Only</span>
          </button>

          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="text-xs py-1.5 px-3 rounded-md border border-[var(--border)] bg-surface text-text cursor-pointer outline-none hover:border-primary transition-colors"
          >
            {CATEGORIES.map((c) => (
              <option key={c.value} value={c.value}>{c.label}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-3 self-end sm:self-auto">
          <Button
            variant="secondary"
            size="sm"
            onClick={loadChanges}
            disabled={loading}
          >
            <RefreshCw size={13} className={`mr-1 ${loading ? 'spin' : ''}`} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            <span>Refresh</span>
          </Button>

          {!loading && changes.length > 0 && (
            <span className="text-xs text-muted pl-3 border-l border-[var(--border)]">
              {meaningfulCount} meaningful · {changes.length} total
            </span>
          )}
        </div>
      </div>

      {/* Main Feed Container with generous vertical gap */}
      {!activeWorkspace ? (
        <div className="card p-16 text-center text-muted border-dashed">
          <p className="text-sm">Please select a workspace to view detected findings.</p>
        </div>
      ) : loading ? (
        <div className="py-24 text-center text-muted text-sm flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 border-3 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
          <span>Analyzing snapshot findings...</span>
        </div>
      ) : error ? (
        <div className="alert-banner alert-error flex items-center gap-2">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      ) : changes.length === 0 ? (
        <div className="card p-16 text-center text-muted border-dashed flex flex-col items-center justify-center gap-2">
          <Inbox size={36} className="text-muted mb-2 opacity-50" />
          <h3 className="text-base font-semibold text-text">No changes detected yet</h3>
          <p className="text-sm max-w-sm mx-auto text-muted">
            Run a scan on your configured competitors to detect live website or pricing changes.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-6">
          {changes.map((change) => (
            <ChangeCard key={change.id} change={change} />
          ))}
        </div>
      )}
    </div>
  );
}
