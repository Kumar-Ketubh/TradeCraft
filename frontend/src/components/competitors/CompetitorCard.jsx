// frontend/src/components/competitors/CompetitorCard.jsx
// Clean, standard CompetitorCard adhering strictly to TradeCraft design tokens

import { useState } from 'react';
import Card from '../ui/Card';
import Button from '../ui/Button';
import { Edit2, Trash2, Play, RefreshCw, CheckCircle2, AlertCircle } from 'lucide-react';
import { api } from '../../services/api';

export default function CompetitorCard({ 
  competitor, 
  onEdit, 
  onDelete, 
  onToggleMonitoring, 
  onConfigureSources,
  onScanComplete,
}) {
  const [scanning, setScanning] = useState(false);
  const [scanResult, setScanResult] = useState(null);

  const handleScan = async () => {
    if (scanning || !competitor?.id) return;
    setScanning(true);
    setScanResult(null);
    try {
      const data = await api.scans.triggerCompetitorScan(competitor.id);
      const isSuccess = data.status === 'completed' && data.successful_sources > 0;
      setScanResult({
        type: isSuccess ? 'success' : 'error',
        message: `Scan ${data.status}: ${data.successful_sources}/${data.total_sources} sources succeeded`,
      });
      if (onScanComplete) {
        onScanComplete(data);
      }
    } catch (err) {
      setScanResult({
        type: 'error',
        message: err.message || 'Scan failed',
      });
    } finally {
      setScanning(false);
    }
  };

  return (
    <Card className="flex flex-col h-full">
      <div className="flex justify-between items-start mb-2">
        <h3 className="font-bold text-lg leading-tight text-text">{competitor.name}</h3>
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

      {/* Scan execution feedback banner */}
      {scanResult && (
        <div 
          className={`mb-3 p-2 text-xs rounded-md border flex items-center justify-between gap-2 ${
            scanResult.type === 'success' 
              ? 'bg-success-light text-success border-[var(--border)]' 
              : 'bg-danger-light text-danger border-[var(--border)]'
          }`}
        >
          <div className="flex items-center gap-1.5 truncate">
            {scanResult.type === 'success' ? (
              <CheckCircle2 size={13} className="shrink-0" />
            ) : (
              <AlertCircle size={13} className="shrink-0" />
            )}
            <span className="truncate">{scanResult.message}</span>
          </div>
          <button 
            type="button" 
            onClick={() => setScanResult(null)}
            className="hover:opacity-75 text-[11px] font-medium shrink-0 ml-1"
          >
            ×
          </button>
        </div>
      )}

      <div className="mt-auto pt-4 border-t border-[var(--border)] flex flex-col gap-3">
        <div className="flex justify-between items-center text-sm">
          <span className="font-medium text-muted">
            Sources: <strong className="text-text">{competitor.source_count || 0}</strong>
          </span>
          <Button variant="ghost" size="sm" onClick={() => onConfigureSources(competitor)}>
            Configure Sources
          </Button>
        </div>

        <div className="flex justify-between items-center gap-2 pt-2 border-t border-[var(--border)]">
          <Button
            variant="secondary"
            size="sm"
            onClick={handleScan}
            disabled={scanning || !competitor.monitoring_enabled}
            title={!competitor.monitoring_enabled ? "Enable monitoring to scan this competitor" : "Trigger scan now"}
            className="flex-1"
          >
            {scanning ? (
              <>
                <RefreshCw size={14} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
                <span>Scanning...</span>
              </>
            ) : (
              <>
                <Play size={14} />
                <span>Scan Now</span>
              </>
            )}
          </Button>

          <div className="flex gap-2">
            <Button variant="secondary" size="sm" onClick={() => onEdit(competitor)} title="Edit">
              <Edit2 size={16} />
            </Button>
            <Button variant="danger" size="sm" onClick={() => onDelete(competitor.id)} title="Delete">
              <Trash2 size={16} />
            </Button>
          </div>
        </div>
      </div>
    </Card>
  );
}
