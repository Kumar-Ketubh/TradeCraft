import { useState, useEffect } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import PageHeader from '../components/ui/PageHeader';
import Button from '../components/ui/Button';
import CompetitorCard from '../components/competitors/CompetitorCard';
import CompetitorForm from '../components/competitors/CompetitorForm';
import SourceList from '../components/competitors/SourceList';
import { Plus } from 'lucide-react';

export default function Competitors() {
  const { activeWorkspace } = useAuth();
  const [competitors, setCompetitors] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const [showCompModal, setShowCompModal] = useState(false);
  const [editingComp, setEditingComp] = useState(null);
  const [saving, setSaving] = useState(false);

  const [selectedCompForSources, setSelectedCompForSources] = useState(null);

  useEffect(() => {
    if (activeWorkspace) {
      fetchCompetitors();
    } else {
      setCompetitors([]);
    }
  }, [activeWorkspace?.id]);

  const fetchCompetitors = async () => {
    if (!activeWorkspace) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.competitors.list(activeWorkspace.id);
      setCompetitors(data || []);
    } catch (err) {
      setError(err.message || 'Failed to fetch competitors');
    } finally {
      setLoading(false);
    }
  };

  const handleOpenAdd = () => {
    setEditingComp(null);
    setShowCompModal(true);
  };

  const handleOpenEdit = (comp) => {
    setEditingComp(comp);
    setShowCompModal(true);
  };

  const handleSaveCompetitor = async (compData) => {
    if (!activeWorkspace) return;
    setSaving(true);
    try {
      if (editingComp) {
        await api.competitors.update(activeWorkspace.id, editingComp.id, compData);
      } else {
        await api.competitors.create(activeWorkspace.id, compData);
      }
      setShowCompModal(false);
      await fetchCompetitors();
    } catch (err) {
      alert(err.message || 'Failed to save competitor');
    } finally {
      setSaving(false);
    }
  };

  const handleToggleMonitoring = async (comp) => {
    if (!activeWorkspace) return;
    try {
      await api.competitors.update(activeWorkspace.id, comp.id, {
        monitoring_enabled: !comp.monitoring_enabled,
      });
      await fetchCompetitors();
    } catch (err) {
      alert(err.message || 'Failed to update status');
    }
  };

  const handleDeleteCompetitor = async (compId) => {
    if (!activeWorkspace) return;
    if (!confirm('Are you sure you want to delete this competitor and all its configured sources?')) return;
    try {
      await api.competitors.delete(activeWorkspace.id, compId);
      await fetchCompetitors();
    } catch (err) {
      alert(err.message || 'Failed to delete competitor');
    }
  };

  if (!activeWorkspace) {
    return (
      <div className="p-12 text-center text-muted border border-[var(--border)] border-dashed rounded-md bg-[var(--surface)]">
        <p>Please select or create a workspace to manage competitors.</p>
      </div>
    );
  }

  return (
    <div>
      <PageHeader 
        title="Competitors" 
        description={`Manage competitors and their monitored public sources for workspace: ${activeWorkspace.name}`}
        action={
          <Button variant="primary" onClick={handleOpenAdd}>
            <Plus size={16} className="mr-1" /> Add Competitor
          </Button>
        }
      />

      {error && <div className="alert-banner alert-error mb-6">{error}</div>}

      {loading ? (
        <div className="p-12 text-center text-muted">Loading competitors...</div>
      ) : competitors.length === 0 ? (
        <div className="p-12 text-center border border-[var(--border)] border-dashed rounded-md bg-[var(--surface)] text-muted">
          <h3 className="text-lg font-semibold text-text mb-2">No competitors configured yet</h3>
          <p className="mb-6">Add your first competitor to begin configuring public URLs and sources.</p>
          <Button variant="primary" onClick={handleOpenAdd}>
            <Plus size={16} className="mr-1" /> Add First Competitor
          </Button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {competitors.map((comp) => (
            <CompetitorCard
              key={comp.id}
              competitor={comp}
              onEdit={handleOpenEdit}
              onDelete={handleDeleteCompetitor}
              onToggleMonitoring={handleToggleMonitoring}
              onConfigureSources={setSelectedCompForSources}
            />
          ))}
        </div>
      )}

      {/* Forms and Modals */}
      <CompetitorForm
        isOpen={showCompModal}
        onClose={() => setShowCompModal(false)}
        onSave={handleSaveCompetitor}
        editingComp={editingComp}
        saving={saving}
      />

      {selectedCompForSources && (
        <SourceList
          competitor={selectedCompForSources}
          onClose={() => setSelectedCompForSources(null)}
          onSourcesUpdated={fetchCompetitors}
        />
      )}
    </div>
  );
}
