import { useState, useEffect, useRef } from 'react';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import Badge from '../ui/Badge';
import { api } from '../../services/api';
import { Copy, Check, ChevronDown, ChevronRight, Clock, AlertTriangle, FileText } from 'lucide-react';

export default function SnapshotHistoryModal({ isOpen, onClose, source }) {
  const [snapshots, setSnapshots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [copiedHash, setCopiedHash] = useState(null);
  const containerRef = useRef(null);

  useEffect(() => {
    // Expand standard modal width for comfortable code and hash viewing
    const modalEl = containerRef.current?.closest('.modal-content');
    if (modalEl) {
      modalEl.style.maxWidth = '780px';
    }
  }, [isOpen]);

  useEffect(() => {
    if (!isOpen || !source?.id) return;

    let isMounted = true;
    const fetchSnapshots = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await api.snapshots.listBySource(source.id);
        if (isMounted) {
          setSnapshots(Array.isArray(data) ? data : []);
          // Auto-expand the latest snapshot if available
          if (Array.isArray(data) && data.length > 0) {
            setExpandedId(data[0].id);
          }
        }
      } catch (err) {
        if (isMounted) {
          setError(err.message || 'Failed to load snapshots');
        }
      } finally {
        if (isMounted) {
          setLoading(false);
        }
      }
    };

    fetchSnapshots();

    return () => {
      isMounted = false;
    };
  }, [isOpen, source?.id]);

  const handleCopyHash = async (hash) => {
    if (!hash) return;
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(hash);
      } else {
        const textArea = document.createElement('textarea');
        textArea.value = hash;
        document.body.appendChild(textArea);
        textArea.select();
        document.execCommand('copy');
        document.body.removeChild(textArea);
      }
      setCopiedHash(hash);
      setTimeout(() => setCopiedHash(null), 2000);
    } catch (err) {
      console.warn('Clipboard write failed:', err);
    }
  };

  const toggleExpand = (snapshotId) => {
    setExpandedId((prev) => (prev === snapshotId ? null : snapshotId));
  };

  const formatDate = (isoString) => {
    if (!isoString) return 'Unknown date';
    try {
      const d = new Date(isoString);
      return d.toLocaleString(undefined, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
        second: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  const getStatusBadge = (snapshot) => {
    const code = snapshot.status_code;
    const isSuccess = snapshot.status === 'success';

    if (code === 200 || (isSuccess && !code)) {
      return <Badge variant="success">{code ? `${code} OK` : '200 OK'}</Badge>;
    }
    if (code) {
      const variant = code >= 400 ? 'danger' : 'warning';
      return <Badge variant={variant}>{code} Error</Badge>;
    }
    return <Badge variant="danger">{snapshot.status || 'Error'}</Badge>;
  };

  if (!isOpen || !source) return null;

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={`Snapshot History: ${source.name}`}>
      <div ref={containerRef} className="space-y-4">
        {/* Source metadata header */}
        <div className="p-3 bg-[var(--bg)] border border-[var(--border)] rounded-md flex flex-col md:flex-row md:items-center justify-between gap-2 text-xs">
          <div>
            <span className="text-muted font-medium mr-2">Target URL:</span>
            <a href={source.url} target="_blank" rel="noreferrer" className="font-mono hover:underline text-[var(--primary)] break-all">
              {source.url}
            </a>
          </div>
          <div className="flex items-center gap-3 shrink-0 text-muted">
            <span>Type: <strong className="text-[var(--text)]">{source.source_type}</strong></span>
            <span>Total Captured: <strong className="text-[var(--text)]">{snapshots.length}</strong></span>
          </div>
        </div>

        {error && (
          <div className="p-3 bg-danger-light text-danger text-sm rounded border border-[var(--border)] flex items-center gap-2">
            <AlertTriangle size={16} />
            <span>{error}</span>
          </div>
        )}

        {loading ? (
          <div className="p-12 text-center text-muted">
            <Clock size={24} className="mx-auto mb-2 opacity-50" />
            <p className="text-sm">Loading snapshot history...</p>
          </div>
        ) : snapshots.length === 0 ? (
          <div className="p-10 text-center border border-[var(--border)] border-dashed rounded-md bg-[var(--bg)] text-muted">
            <FileText size={28} className="mx-auto mb-2 opacity-50" />
            <h4 className="font-semibold text-text mb-1">No snapshots recorded yet</h4>
            <p className="text-xs max-w-sm mx-auto">
              This source has not been scanned yet. Trigger a scan from the Dashboard or Competitors view to capture its first snapshot.
            </p>
          </div>
        ) : (
          <div className="space-y-3 max-h-[60vh] overflow-y-auto pr-1">
            {snapshots.map((snap) => {
              const isExpanded = expandedId === snap.id;
              const hasHash = Boolean(snap.content_hash);
              const isCopied = copiedHash === snap.content_hash;

              return (
                <div
                  key={snap.id}
                  className="border border-[var(--border)] rounded-md bg-[var(--surface)] overflow-hidden transition-all shadow-sm"
                >
                  {/* Snapshot summary header row */}
                  <div className="p-3 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-[var(--surface)] border-b border-[var(--border)]">
                    <div className="flex items-center gap-2 flex-wrap">
                      {getStatusBadge(snap)}
                      <span className="text-xs text-muted flex items-center gap-1 font-medium">
                        <Clock size={13} />
                        {formatDate(snap.created_at)}
                      </span>
                      {snap.response_time_ms !== null && snap.response_time_ms !== undefined && (
                        <span className="text-xs text-muted">
                          ({snap.response_time_ms}ms)
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 flex-wrap justify-end">
                      {hasHash && (
                        <div className="flex items-center gap-1 bg-[var(--bg)] px-2 py-0.5 rounded border border-[var(--border)]">
                          <span className="text-[10px] text-muted uppercase font-semibold">SHA-256:</span>
                          <code className="font-mono text-xs text-[var(--text)]">
                            {snap.content_hash.slice(0, 8)}...{snap.content_hash.slice(-6)}
                          </code>
                          <button
                            type="button"
                            onClick={() => handleCopyHash(snap.content_hash)}
                            className="text-muted hover:text-[var(--text)] ml-1 p-0.5"
                            title="Copy full SHA-256 hash"
                          >
                            {isCopied ? (
                              <Check size={13} className="text-success" />
                            ) : (
                              <Copy size={13} />
                            )}
                          </button>
                        </div>
                      )}

                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => toggleExpand(snap.id)}
                        className="text-xs py-1 px-2"
                        title={isExpanded ? "Collapse normalized text" : "Expand normalized text"}
                      >
                        {isExpanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                        <span>{isExpanded ? 'Hide Content' : 'View Content'}</span>
                      </Button>
                    </div>
                  </div>

                  {/* Error banner if snapshot failed */}
                  {snap.error_message && (
                    <div className="p-2.5 bg-danger-light text-danger text-xs border-b border-[var(--border)] flex items-start gap-2">
                      <AlertTriangle size={14} className="shrink-0 mt-0.5" />
                      <div>
                        <strong>Capture Error:</strong> {snap.error_message}
                      </div>
                    </div>
                  )}

                  {/* Expandable Normalized Content Viewer */}
                  {isExpanded && (
                    <div className="p-3 bg-[var(--bg)]">
                      <div className="flex justify-between items-center mb-2">
                        <span className="text-xs font-semibold text-muted uppercase tracking-wider">
                          Normalized Extracted Content:
                        </span>
                        <div className="flex items-center gap-2 text-xs text-muted font-mono">
                          {snap.normalized_content ? (
                            <span>{snap.normalized_content.length} characters</span>
                          ) : (
                            <span>Empty content</span>
                          )}
                        </div>
                      </div>

                      {snap.normalized_content ? (
                        <pre className="whitespace-pre-wrap font-mono text-xs text-[var(--text)] max-h-56 overflow-y-auto bg-[var(--surface)] p-3 rounded border border-[var(--border)] leading-relaxed select-text">
                          {snap.normalized_content}
                        </pre>
                      ) : (
                        <div className="p-4 text-center text-xs text-muted italic bg-[var(--surface)] rounded border border-[var(--border)]">
                          {snap.status === 'error'
                            ? 'No normalized content available due to capture error.'
                            : 'No text extracted from this snapshot.'}
                        </div>
                      )}

                      {hasHash && (
                        <div className="mt-2 text-[11px] text-muted flex items-center justify-between">
                          <span className="font-mono break-all">
                            Full Hash: {snap.content_hash}
                          </span>
                          <button
                            type="button"
                            onClick={() => handleCopyHash(snap.content_hash)}
                            className="text-[var(--primary)] hover:underline ml-2 shrink-0"
                          >
                            {isCopied ? 'Copied!' : 'Copy Hash'}
                          </button>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        <div className="flex justify-end pt-2 border-t border-[var(--border)]">
          <Button variant="secondary" size="sm" onClick={onClose}>
            Close
          </Button>
        </div>
      </div>
    </Modal>
  );
}
