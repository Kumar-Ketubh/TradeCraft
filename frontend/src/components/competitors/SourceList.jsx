import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import Badge from '../ui/Badge';
import { Edit2, Trash2 } from 'lucide-react';

const SOURCE_TYPES = [
  { value: 'website', label: 'Main Website' },
  { value: 'product_page', label: 'Product Page' },
  { value: 'pricing', label: 'Pricing Page' },
  { value: 'blog', label: 'Blog / Newsroom' },
  { value: 'documentation', label: 'Docs / API' },
  { value: 'rss', label: 'RSS Feed' },
  { value: 'news', label: 'Press Releases' },
  { value: 'other', label: 'Other Public URL' },
];

export default function SourceList({ competitor, onClose, onSourcesUpdated }) {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [editingSource, setEditingSource] = useState(null);
  const [showForm, setShowForm] = useState(false);
  const [name, setName] = useState('');
  const [url, setUrl] = useState('');
  const [sourceType, setSourceType] = useState('pricing');
  const [monitoringEnabled, setMonitoringEnabled] = useState(true);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (competitor?.id) {
      fetchSources();
    }
  }, [competitor?.id]);

  const fetchSources = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.sources.list(competitor.id);
      setSources(data || []);
      if (onSourcesUpdated) onSourcesUpdated();
    } catch (err) {
      setError(err.message || 'Failed to load sources');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAdd = () => {
    setEditingSource(null);
    setName('');
    setUrl('');
    setSourceType('pricing');
    setMonitoringEnabled(true);
    setShowForm(true);
  };

  const handleOpenEdit = (src) => {
    setEditingSource(src);
    setName(src.name);
    setUrl(src.url);
    setSourceType(src.source_type || 'website');
    setMonitoringEnabled(src.monitoring_enabled);
    setShowForm(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!name.trim() || !url.trim()) return;
    setSubmitting(true);
    try {
      if (editingSource) {
        await api.sources.update(competitor.id, editingSource.id, {
          name: name.trim(),
          url: url.trim(),
          source_type: sourceType,
          monitoring_enabled: monitoringEnabled,
        });
      } else {
        await api.sources.create(competitor.id, {
          name: name.trim(),
          url: url.trim(),
          source_type: sourceType,
          monitoring_enabled: monitoringEnabled,
        });
      }
      setShowForm(false);
      await fetchSources();
    } catch (err) {
      alert(err.message || 'Failed to save source');
    } finally {
      setSubmitting(false);
    }
  };

  const handleToggleMonitoring = async (src) => {
    try {
      await api.sources.update(competitor.id, src.id, {
        monitoring_enabled: !src.monitoring_enabled,
      });
      await fetchSources();
    } catch (err) {
      alert(err.message || 'Failed to update monitoring status');
    }
  };

  const handleDelete = async (srcId) => {
    if (!confirm('Are you sure you want to remove this configured source?')) return;
    try {
      await api.sources.delete(competitor.id, srcId);
      await fetchSources();
    } catch (err) {
      alert(err.message || 'Failed to delete source');
    }
  };

  if (!competitor) return null;

  return (
    <Modal isOpen={true} onClose={onClose} title={`Sources for ${competitor.name}`}>
      {error && <div className="alert-banner alert-error">{error}</div>}

      <div className="flex justify-end mb-4">
        <Button variant="primary" size="sm" onClick={handleOpenAdd}>
          + Add Source
        </Button>
      </div>

      {showForm && (
        <div className="bg-[var(--bg)] border border-[var(--border)] rounded-md p-4 mb-4">
          <h4 className="font-semibold mb-4">{editingSource ? 'Edit Source' : 'Add Source'}</h4>
          <form onSubmit={handleSubmit}>
            <div className="grid md:grid-cols-2 gap-4">
              <div className="form-group">
                <label>Source Name</label>
                <input
                  type="text"
                  className="form-control"
                  placeholder="e.g. Official Pricing"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Source URL</label>
                <input
                  type="url"
                  className="form-control"
                  placeholder="https://example.com/pricing"
                  value={url}
                  onChange={(e) => setUrl(e.target.value)}
                  required
                />
              </div>
              <div className="form-group">
                <label>Category / Type</label>
                <select 
                  className="form-control"
                  value={sourceType} 
                  onChange={(e) => setSourceType(e.target.value)}
                >
                  {SOURCE_TYPES.map((t) => (
                    <option key={t.value} value={t.value}>{t.label}</option>
                  ))}
                </select>
              </div>
              <div className="form-group flex items-center gap-2 mt-6">
                <input
                  type="checkbox"
                  id="sourceMonitoring"
                  checked={monitoringEnabled}
                  onChange={(e) => setMonitoringEnabled(e.target.checked)}
                />
                <label htmlFor="sourceMonitoring" className="mb-0">Enable Monitoring</label>
              </div>
            </div>
            <div className="flex justify-end gap-2 mt-4">
              <Button type="button" variant="secondary" size="sm" onClick={() => setShowForm(false)}>
                Cancel
              </Button>
              <Button type="submit" variant="primary" size="sm" disabled={submitting || !name.trim()}>
                {submitting ? 'Saving...' : 'Save Source'}
              </Button>
            </div>
          </form>
        </div>
      )}

      {loading ? (
        <div className="p-8 text-center text-muted">Loading sources...</div>
      ) : sources.length === 0 ? (
        <div className="p-8 text-center border border-[var(--border)] rounded-md bg-[var(--bg)] text-muted">
          <p>No public sources configured yet.</p>
        </div>
      ) : (
        <div className="table-wrapper">
          <table className="table">
            <thead>
              <tr>
                <th>Source</th>
                <th>URL</th>
                <th>Type</th>
                <th>Monitoring</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {sources.map((src) => (
                <tr key={src.id}>
                  <td className="font-medium text-[var(--text)]">{src.name}</td>
                  <td>
                    <a href={src.url} target="_blank" rel="noreferrer" className="text-sm">
                      {src.url.length > 30 ? src.url.substring(0, 30) + '...' : src.url}
                    </a>
                  </td>
                  <td>
                    <Badge variant="primary">{src.source_type}</Badge>
                  </td>
                  <td>
                    <button
                      className={`badge-btn ${src.monitoring_enabled ? 'badge-active' : 'badge-inactive'}`}
                      onClick={() => handleToggleMonitoring(src)}
                    >
                      {src.monitoring_enabled ? 'Enabled' : 'Disabled'}
                    </button>
                  </td>
                  <td>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="sm" onClick={() => handleOpenEdit(src)} title="Edit">
                        <Edit2 size={16} />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(src.id)} title="Delete" className="text-danger">
                        <Trash2 size={16} />
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Modal>
  );
}
