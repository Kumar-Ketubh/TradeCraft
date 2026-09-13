// frontend/src/components/WorkspaceSelector.jsx
import { useState } from 'react';

export default function WorkspaceSelector({ workspaces, activeWorkspace, onSelectWorkspace, onCreateWorkspace }) {
  const [isCreating, setIsCreating] = useState(false);
  const [newWsName, setNewWsName] = useState('');
  const [loading, setLoading] = useState(false);

  const handleCreate = async (e) => {
    e.preventDefault();
    if (!newWsName.trim()) return;
    setLoading(true);
    try {
      await onCreateWorkspace(newWsName.trim());
      setNewWsName('');
      setIsCreating(false);
    } catch (err) {
      alert(err.message || 'Failed to create workspace');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="workspace-selector-container">
      <div className="workspace-selector-label">Workspace</div>
      <div className="workspace-selector-controls">
        <select
          className="workspace-dropdown"
          value={activeWorkspace ? activeWorkspace.id : ''}
          onChange={(e) => {
            const ws = workspaces.find((w) => w.id === e.target.value);
            if (ws) onSelectWorkspace(ws);
          }}
        >
          {workspaces.length === 0 && <option value="">No Workspaces</option>}
          {workspaces.map((ws) => (
            <option key={ws.id} value={ws.id}>
              {ws.name} ({ws.competitor_count || 0} competitors)
            </option>
          ))}
        </select>
        <button
          className="btn btn-secondary btn-sm"
          onClick={() => setIsCreating(true)}
          title="Create New Workspace"
        >
          + New Workspace
        </button>
      </div>

      {isCreating && (
        <div className="modal-overlay" onClick={() => setIsCreating(false)}>
          <div className="modal-content modal-sm" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3>Create Workspace</h3>
              <button className="modal-close-btn" onClick={() => setIsCreating(false)}>&times;</button>
            </div>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Workspace Name</label>
                <input
                  type="text"
                  placeholder="e.g. Enterprise Competitors"
                  value={newWsName}
                  onChange={(e) => setNewWsName(e.target.value)}
                  autoFocus
                  required
                />
              </div>
              <div className="modal-actions">
                <button type="button" className="btn btn-secondary" onClick={() => setIsCreating(false)}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={loading}>
                  {loading ? 'Creating...' : 'Create Workspace'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
