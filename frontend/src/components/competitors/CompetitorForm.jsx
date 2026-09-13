import { useState, useEffect } from 'react';
import Modal from '../ui/Modal';
import Button from '../ui/Button';

export default function CompetitorForm({ isOpen, onClose, onSave, editingComp, saving }) {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [website, setWebsite] = useState('');
  const [monitoringEnabled, setMonitoringEnabled] = useState(true);

  useEffect(() => {
    if (editingComp) {
      setName(editingComp.name);
      setDescription(editingComp.description || '');
      setWebsite(editingComp.website || '');
      setMonitoringEnabled(editingComp.monitoring_enabled);
    } else {
      setName('');
      setDescription('');
      setWebsite('');
      setMonitoringEnabled(true);
    }
  }, [editingComp, isOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onSave({
      name: name.trim(),
      description: description.trim() || null,
      website: website.trim() || null,
      monitoring_enabled: monitoringEnabled,
    });
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title={editingComp ? 'Edit Competitor' : 'Add New Competitor'}>
      <form onSubmit={handleSubmit}>
        <div className="form-group">
          <label>Competitor Name</label>
          <input
            type="text"
            className="form-control"
            placeholder="e.g. Acme Corp"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
        </div>

        <div className="form-group">
          <label>Description / Notes</label>
          <textarea
            className="form-control"
            placeholder="Key products, market positioning..."
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            rows={3}
          />
        </div>

        <div className="form-group">
          <label>Official Website URL</label>
          <input
            type="url"
            className="form-control"
            placeholder="https://example.com"
            value={website}
            onChange={(e) => setWebsite(e.target.value)}
          />
        </div>

        <div className="form-group flex items-center gap-2 mt-4">
          <input
            type="checkbox"
            id="monitoringEnabled"
            checked={monitoringEnabled}
            onChange={(e) => setMonitoringEnabled(e.target.checked)}
          />
          <label htmlFor="monitoringEnabled" className="mb-0">Enable Competitor Monitoring</label>
        </div>

        <div className="modal-footer">
          <Button type="button" variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button type="submit" variant="primary" disabled={saving || !name.trim()}>
            {saving ? 'Saving...' : editingComp ? 'Update Competitor' : 'Save Competitor'}
          </Button>
        </div>
      </form>
    </Modal>
  );
}
