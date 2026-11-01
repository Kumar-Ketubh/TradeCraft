// frontend/src/pages/Proposal.jsx
// Complete Proposal Generation and Management Interface

import { useState, useEffect, useCallback } from 'react';
import PageHeader from '../components/ui/PageHeader';
import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import Badge from '../components/ui/Badge';
import Modal from '../components/ui/Modal';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import {
  FileText,
  Plus,
  Sparkles,
  ShieldCheck,
  CheckCircle2,
  Calendar,
  Target,
  Edit3,
  Save,
  Trash2,
  AlertCircle,
  Inbox,
  Maximize2,
  Download,
  Printer,
  Copy,
  Check,
} from 'lucide-react';
import ProposalReaderModal from '../components/proposals/ProposalReaderModal';

export default function Proposal() {
  const { activeWorkspace } = useAuth();
  const [proposals, setProposals] = useState([]);
  const [selectedProposal, setSelectedProposal] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [copiedMain, setCopiedMain] = useState(false);

  // Pop-Out Glass Modal State
  const [showPopout, setShowPopout] = useState(false);

  // Proposal Generation Modal State
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [title, setTitle] = useState('');
  const [targetGoal, setTargetGoal] = useState('');
  const [verifiedFindings, setVerifiedFindings] = useState([]);
  const [selectedFindingIds, setSelectedFindingIds] = useState([]);
  const [generating, setGenerating] = useState(false);
  const [generateError, setGenerateError] = useState(null);

  // Edit Mode State
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [savingEdit, setSavingEdit] = useState(false);

  const loadProposals = useCallback(async () => {
    if (!activeWorkspace?.id) return;
    setLoading(true);
    setError(null);
    try {
      const data = await api.proposals.listByWorkspace(activeWorkspace.id);
      const list = Array.isArray(data) ? data : [];
      setProposals(list);
      if (list.length > 0 && !selectedProposal) {
        setSelectedProposal(list[0]);
      }
    } catch (err) {
      setError(err.message || 'Failed to load proposals');
    } finally {
      setLoading(false);
    }
  }, [activeWorkspace?.id]);

  useEffect(() => {
    loadProposals();
  }, [loadProposals]);

  // Load verified findings when opening create modal
  const openCreateModal = async () => {
    setShowCreateModal(true);
    setGenerateError(null);
    setTitle('');
    setTargetGoal('');
    setSelectedFindingIds([]);
    try {
      if (activeWorkspace?.id) {
        const findings = await api.findings.listByWorkspace(activeWorkspace.id, {
          verification_status: 'VERIFIED',
        });
        const list = Array.isArray(findings) ? findings : [];
        setVerifiedFindings(list);
        setSelectedFindingIds(list.map((f) => f.id)); // Default to all verified
      }
    } catch (e) {
      console.error('Failed to load verified findings:', e);
    }
  };

  const handleGenerate = async (e) => {
    e.preventDefault();
    if (!title.trim()) {
      setGenerateError('Please provide a proposal title');
      return;
    }
    setGenerating(true);
    setGenerateError(null);
    try {
      const created = await api.proposals.create(activeWorkspace.id, {
        title,
        target_goal: targetGoal || 'Competitive Counter-Positioning',
        finding_ids: selectedFindingIds,
      });
      setProposals((prev) => [created, ...prev]);
      setSelectedProposal(created);
      setShowCreateModal(false);
    } catch (err) {
      setGenerateError(err.message || 'Proposal generation failed');
    } finally {
      setGenerating(false);
    }
  };

  const handleSaveEdit = async () => {
    if (!selectedProposal) return;
    setSavingEdit(true);
    try {
      const updated = await api.proposals.update(selectedProposal.id, {
        markdown_content: editContent,
      });
      setSelectedProposal(updated);
      setProposals((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
      setIsEditing(false);
    } catch (err) {
      alert('Failed to save edits: ' + err.message);
    } finally {
      setSavingEdit(false);
    }
  };

  const handleToggleStatus = async () => {
    if (!selectedProposal) return;
    const newStatus = selectedProposal.status === 'FINALIZED' ? 'DRAFT' : 'FINALIZED';
    try {
      const updated = await api.proposals.update(selectedProposal.id, {
        status: newStatus,
      });
      setSelectedProposal(updated);
      setProposals((prev) => prev.map((p) => (p.id === updated.id ? updated : p)));
    } catch (err) {
      alert('Failed to update proposal status: ' + err.message);
    }
  };

  const handleSaveModalContent = async (proposalId, newContent) => {
    const updated = await api.proposals.update(proposalId, {
      markdown_content: newContent,
    });
    setProposals((prev) => prev.map((p) => (p.id === proposalId ? updated : p)));
    if (selectedProposal?.id === proposalId) {
      setSelectedProposal(updated);
      setEditContent(newContent);
    }
  };

  const handleToggleStatusFromModal = async (proposalId) => {
    const current = proposals.find((p) => p.id === proposalId) || selectedProposal;
    if (!current) return;
    const newStatus = current.status === 'FINALIZED' ? 'DRAFT' : 'FINALIZED';
    const updated = await api.proposals.update(proposalId, { status: newStatus });
    setProposals((prev) => prev.map((p) => (p.id === proposalId ? updated : p)));
    if (selectedProposal?.id === proposalId) {
      setSelectedProposal(updated);
    }
  };

  const downloadProposalMarkdown = (p = selectedProposal) => {
    if (!p) return;
    const cleanTitle = (p.title || 'tradecraft-proposal')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
    const filename = `${cleanTitle}.md`;
    const blob = new Blob([p.markdown_content || ''], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleCopyMain = async () => {
    if (!selectedProposal?.markdown_content) return;
    try {
      await navigator.clipboard.writeText(selectedProposal.markdown_content);
      setCopiedMain(true);
      setTimeout(() => setCopiedMain(false), 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  const handleDelete = async (proposalId) => {
    if (!confirm('Are you sure you want to delete this proposal?')) return;
    try {
      await api.proposals.delete(proposalId);
      const remaining = proposals.filter((p) => p.id !== proposalId);
      setProposals(remaining);
      setSelectedProposal(remaining[0] || null);
    } catch (err) {
      alert('Failed to delete proposal: ' + err.message);
    }
  };

  const toggleFindingSelection = (id) => {
    setSelectedFindingIds((prev) =>
      prev.includes(id) ? prev.filter((item) => item !== id) : [...prev, id]
    );
  };

  return (
    <div className="space-y-8 max-w-6xl mx-auto pb-16">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <PageHeader
          title="Executive Proposals"
          description="Synthesize verified competitor findings into rigorous, 7-section counter-proposals."
        />
        <Button variant="primary" onClick={openCreateModal} className="self-start sm:self-auto">
          <Plus size={14} className="mr-1.5" />
          <span>New Proposal</span>
        </Button>
      </div>

      {!activeWorkspace ? (
        <div className="card p-16 text-center text-muted border-dashed">
          <p className="text-sm">Please select a workspace to manage strategic proposals.</p>
        </div>
      ) : loading ? (
        <div className="py-24 text-center text-muted text-sm flex flex-col items-center justify-center gap-3">
          <div className="w-8 h-8 border-3 border-[var(--primary)] border-t-transparent rounded-full animate-spin" />
          <span>Loading strategic proposals...</span>
        </div>
      ) : error ? (
        <div className="alert-banner alert-error flex items-center gap-2">
          <AlertCircle size={16} />
          <span>{error}</span>
        </div>
      ) : proposals.length === 0 ? (
        /* Empty State with Workflow Diagram */
        <Card title="Proposal Generation Pipeline" className="max-w-3xl mx-auto text-center p-8">
          <div className="flex flex-col sm:flex-row items-center justify-center gap-2 my-8 text-xs font-semibold">
            <div className="p-3 bg-[var(--bg)] border border-[var(--border)] rounded-lg text-center w-40">
              <ShieldCheck size={16} className="mx-auto mb-1 text-emerald-500" />
              Verified Finding
            </div>
            <span className="text-muted hidden sm:inline">→</span>
            <span className="text-muted sm:hidden">↓</span>
            <div className="p-3 bg-[var(--bg)] border border-[var(--border)] rounded-lg text-center w-40">
              <FileText size={16} className="mx-auto mb-1 text-purple-400" />
              Grounded Quotes
            </div>
            <span className="text-muted hidden sm:inline">→</span>
            <span className="text-muted sm:hidden">↓</span>
            <div className="p-3 bg-[var(--bg)] border border-[var(--border)] rounded-lg text-center w-40">
              <Sparkles size={16} className="mx-auto mb-1 text-amber-400" />
              LangGraph Synthesis
            </div>
            <span className="text-muted hidden sm:inline">→</span>
            <span className="text-muted sm:hidden">↓</span>
            <div className="p-3 bg-[var(--primary-bg)] border border-[var(--primary)] text-[var(--primary)] rounded-lg text-center w-40 shadow-sm">
              <Target size={16} className="mx-auto mb-1" />
              7-Section Proposal
            </div>
          </div>

          <div className="p-6 bg-[var(--bg)] rounded-xl border border-[var(--border)] border-dashed max-w-lg mx-auto space-y-4">
            <h3 className="text-base font-semibold text-text">No proposals generated yet</h3>
            <p className="text-xs text-muted leading-relaxed">
              Synthesize strategic counter-proposals citing verbatim evidence quotes from verified competitor moves.
            </p>
            <Button variant="primary" onClick={openCreateModal}>
              <Sparkles size={14} className="mr-1.5" />
              <span>Generate First Proposal</span>
            </Button>
          </div>
        </Card>
      ) : (
        /* Proposals Master-Detail View */
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 items-start">
          {/* Proposals Sidebar List */}
          <div className="card p-4 space-y-2 lg:col-span-1">
            <div className="flex items-center justify-between pb-3 border-b border-[var(--border)]">
              <span className="text-xs font-semibold uppercase text-muted tracking-wider">
                Proposals ({proposals.length})
              </span>
            </div>

            <div className="divide-y divide-[var(--border)] max-h-[650px] overflow-y-auto">
              {proposals.map((p) => {
                const isSelected = selectedProposal?.id === p.id;
                const dateStr = new Date(p.created_at).toLocaleDateString(undefined, {
                  month: 'short',
                  day: 'numeric',
                });

                return (
                  <div
                    key={p.id}
                    onClick={() => {
                      setSelectedProposal(p);
                      setIsEditing(false);
                      setShowPopout(true);
                    }}
                    className={`py-3 px-3 cursor-pointer rounded-lg transition-colors flex flex-col gap-1.5 ${
                      isSelected
                        ? 'bg-[var(--primary-bg)] border border-[var(--primary)]'
                        : 'hover:bg-[var(--bg)]'
                    }`}
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="text-xs font-bold text-text truncate">
                        {p.title}
                      </span>
                      <Badge variant={p.status === 'FINALIZED' ? 'success' : 'neutral'}>
                        {p.status}
                      </Badge>
                    </div>

                    {p.target_goal && (
                      <p className="text-2xs text-muted line-clamp-1 flex items-center gap-1">
                        <Target size={11} className="shrink-0" />
                        <span>{p.target_goal}</span>
                      </p>
                    )}

                    <div className="flex items-center justify-between text-2xs text-muted pt-1">
                      <span className="flex items-center gap-1">
                        <Calendar size={11} />
                        {dateStr}
                      </span>
                      <div className="flex items-center gap-2">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            downloadProposalMarkdown(p);
                          }}
                          className="text-muted hover:text-primary opacity-60 hover:opacity-100 p-0.5 rounded transition-colors"
                          title="Download .md file"
                        >
                          <Download size={12} />
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handleDelete(p.id);
                          }}
                          className="text-muted hover:text-red-400 opacity-60 hover:opacity-100 p-0.5 rounded transition-colors"
                          title="Delete proposal"
                        >
                          <Trash2 size={12} />
                        </button>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Selected Proposal Reader / Editor */}
          {selectedProposal && (
            <div
              className={`card p-6 space-y-5 lg:col-span-2 transition-all duration-200 ${
                isEditing ? 'border-neutral-800' : ''
              }`}
              style={
                isEditing
                  ? { backgroundColor: '#000000', color: '#ffffff', borderColor: '#262626' }
                  : {}
              }
            >
              <div
                className={`flex flex-col xl:flex-row xl:items-start justify-between gap-4 pb-4 border-b ${
                  isEditing ? 'border-neutral-800' : 'border-[var(--border)]'
                }`}
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 mb-1 flex-wrap">
                    <h2
                      className={`text-lg font-bold m-0 truncate ${
                        isEditing ? 'text-white' : 'text-text'
                      }`}
                    >
                      {selectedProposal.title}
                    </h2>
                    <Badge
                      variant={selectedProposal.status === 'FINALIZED' ? 'success' : 'neutral'}
                    >
                      {selectedProposal.status}
                    </Badge>
                  </div>
                  {selectedProposal.target_goal && (
                    <p
                      className={`text-xs flex items-center gap-1.5 ${
                        isEditing ? 'text-neutral-400' : 'text-muted'
                      }`}
                    >
                      <Target size={13} className="text-[var(--primary)] shrink-0" />
                      <span className="truncate"><strong>Goal:</strong> {selectedProposal.target_goal}</span>
                    </p>
                  )}
                </div>

                <div className="flex items-center gap-1.5 flex-wrap shrink-0">
                  <Button
                    variant="primary"
                    size="sm"
                    onClick={() => setShowPopout(true)}
                    className="text-xs px-2.5 py-1 whitespace-nowrap"
                    title="Pop out in full browser glass window"
                  >
                    <Maximize2 size={13} className="mr-1" />
                    <span>Pop Out</span>
                  </Button>

                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => downloadProposalMarkdown(selectedProposal)}
                    className={`text-xs px-2.5 py-1 whitespace-nowrap ${isEditing ? 'border-neutral-700 text-neutral-300 hover:bg-neutral-900' : ''}`}
                    title="Download proposal as Markdown (.md)"
                  >
                    <Download size={13} className="mr-1" />
                    <span>Download</span>
                  </Button>

                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={() => window.print()}
                    className={`text-xs px-2.5 py-1 whitespace-nowrap ${isEditing ? 'border-neutral-700 text-neutral-300 hover:bg-neutral-900' : ''}`}
                    title="Export or print PDF"
                  >
                    <Printer size={13} className="mr-1" />
                    <span>PDF</span>
                  </Button>

                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleCopyMain}
                    className={`text-xs px-2.5 py-1 whitespace-nowrap ${isEditing ? 'border-neutral-700 text-neutral-300 hover:bg-neutral-900' : ''}`}
                    title="Copy markdown to clipboard"
                  >
                    {copiedMain ? (
                      <>
                        <Check size={13} className="mr-1 text-success" />
                        <span className="text-success">Copied!</span>
                      </>
                    ) : (
                      <>
                        <Copy size={13} className="mr-1" />
                        <span>Copy</span>
                      </>
                    )}
                  </Button>

                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleToggleStatus}
                    className={`text-xs px-2.5 py-1 whitespace-nowrap ${isEditing ? 'border-neutral-700 text-neutral-300 hover:bg-neutral-900' : ''}`}
                  >
                    {selectedProposal.status === 'FINALIZED' ? 'Draft' : 'Finalize'}
                  </Button>

                  {isEditing ? (
                    <div className="flex items-center gap-1.5">
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => setIsEditing(false)}
                        className="text-xs px-2.5 py-1 border-neutral-700 text-neutral-300 hover:bg-neutral-900"
                      >
                        Cancel
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        onClick={handleSaveEdit}
                        disabled={savingEdit}
                        className="text-xs px-2.5 py-1"
                      >
                        <Save size={13} className="mr-1" />
                        <span>{savingEdit ? 'Saving...' : 'Save'}</span>
                      </Button>
                    </div>
                  ) : (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setEditContent(selectedProposal.markdown_content);
                        setIsEditing(true);
                      }}
                      className="text-xs px-2.5 py-1 whitespace-nowrap"
                    >
                      <Edit3 size={13} className="mr-1" />
                      <span>Edit</span>
                    </Button>
                  )}
                </div>
              </div>

              {/* Proposal Content Body with bounded scroll */}
              {isEditing ? (
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <span className="text-xs text-neutral-400 font-medium">Edit Markdown Source:</span>
                    <span className="text-2xs text-neutral-500 font-mono">Editor Theme: Black</span>
                  </div>
                  <textarea
                    rows={18}
                    value={editContent}
                    onChange={(e) => setEditContent(e.target.value)}
                    className="w-full font-mono text-xs p-4 rounded-lg outline-none focus:border-primary transition-colors leading-relaxed glass-scroll"
                    style={{
                      backgroundColor: '#000000',
                      color: '#ffffff',
                      border: '1px solid #262626',
                      maxHeight: '520px',
                    }}
                    placeholder="Enter proposal markdown content..."
                  />
                </div>
              ) : (
                <div
                  className="glass-scroll p-6 rounded-xl border border-[var(--border)] bg-[var(--bg)] text-text space-y-4 text-xs leading-relaxed"
                  style={{
                    height: '520px',
                    maxHeight: '520px',
                    overflowY: 'scroll',
                    scrollBehavior: 'smooth',
                    overscrollBehavior: 'contain',
                  }}
                >
                  <div className="whitespace-pre-wrap font-sans space-y-3 leading-relaxed">
                    {selectedProposal.markdown_content}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Generate Proposal Modal */}
      <Modal
        isOpen={showCreateModal}
        onClose={() => !generating && setShowCreateModal(false)}
        title="Synthesize Strategic Proposal"
      >
        <form onSubmit={handleGenerate} className="space-y-5 text-sm">
          {generateError && (
            <div className="p-3 text-xs rounded bg-red-950/30 border border-red-800 text-red-300">
              {generateError}
            </div>
          )}

          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Proposal Title *
            </label>
            <input
              type="text"
              required
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g. Counter-Strategy to Competitor Commercial Tiering"
              className="w-full text-xs p-2.5 rounded-md border border-[var(--border)] text-black placeholder:text-gray-500 outline-none focus:border-primary"
              style={{ color: '#000000', backgroundColor: '#ffffff' }}
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-text mb-1">
              Target Initiative / Business Goal
            </label>
            <input
              type="text"
              value={targetGoal}
              onChange={(e) => setTargetGoal(e.target.value)}
              placeholder="e.g. Prevent entry-tier churn & update sales battlecard"
              className="w-full text-xs p-2.5 rounded-md border border-[var(--border)] text-black placeholder:text-gray-500 outline-none focus:border-primary"
              style={{ color: '#000000', backgroundColor: '#ffffff' }}
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-xs font-semibold text-text">
                Select Verified Findings to Include:
              </label>
              <span className="text-2xs text-muted">
                {selectedFindingIds.length} of {verifiedFindings.length} selected
              </span>
            </div>

            {verifiedFindings.length === 0 ? (
              <div className="p-4 bg-[var(--bg)] border border-[var(--border)] rounded-md text-xs text-muted text-center">
                No VERIFIED findings available yet in this workspace. Run scans to generate evidence-grounded findings.
              </div>
            ) : (
              <div className="space-y-2 max-h-48 overflow-y-auto p-2 bg-[var(--bg)] rounded-md border border-[var(--border)]">
                {verifiedFindings.map((f) => (
                  <label
                    key={f.id}
                    className="flex items-start gap-2.5 p-2 rounded hover:bg-[var(--surface)] cursor-pointer text-xs"
                  >
                    <input
                      type="checkbox"
                      checked={selectedFindingIds.includes(f.id)}
                      onChange={() => toggleFindingSelection(f.id)}
                      className="mt-0.5 rounded border-[var(--border)] text-primary focus:ring-0 cursor-pointer"
                    />
                    <div className="flex-1">
                      <div className="flex items-center gap-2">
                        <strong className="text-text">{f.title}</strong>
                        <Badge variant="success">
                          {f.grounding_score}% EGA
                        </Badge>
                      </div>
                      <p className="text-2xs text-muted line-clamp-1">{f.factual_summary}</p>
                    </div>
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="pt-3 border-t border-[var(--border)] flex items-center justify-end gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={() => setShowCreateModal(false)}
              disabled={generating}
            >
              Cancel
            </Button>
            <Button
              type="submit"
              variant="primary"
              disabled={generating}
            >
              <Sparkles size={14} className={`mr-1.5 ${generating ? 'animate-spin' : ''}`} />
              <span>{generating ? 'Synthesizing Proposal...' : 'Generate Proposal'}</span>
            </Button>
          </div>
        </form>
      </Modal>

      {/* Pop-Out Glass Reader & Export Modal */}
      <ProposalReaderModal
        isOpen={showPopout}
        onClose={() => setShowPopout(false)}
        proposal={selectedProposal}
        onSaveContent={handleSaveModalContent}
        onToggleStatus={handleToggleStatusFromModal}
      />
    </div>
  );
}
