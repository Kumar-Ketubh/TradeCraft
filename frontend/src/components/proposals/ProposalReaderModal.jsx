// frontend/src/components/proposals/ProposalReaderModal.jsx
// Expansive, glass-tinted pop-out window covering browser space for reading, editing, and exporting proposals.

import { useState, useEffect } from 'react';
import Badge from '../ui/Badge';
import Button from '../ui/Button';
import {
  X,
  Download,
  Printer,
  Copy,
  Check,
  Edit3,
  Save,
  Target,
  Calendar,
  FileText,
  Quote,
  ExternalLink,
  Sparkles,
  Maximize2,
  CheckCircle2,
} from 'lucide-react';

export default function ProposalReaderModal({
  isOpen,
  onClose,
  proposal,
  onSaveContent,
  onToggleStatus,
}) {
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState('');
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (proposal) {
      setEditContent(proposal.markdown_content || '');
      setIsEditing(false);
    }
  }, [proposal]);

  // Handle ESC key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && isOpen) {
        if (isEditing) {
          setIsEditing(false);
        } else {
          onClose();
        }
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isEditing, onClose]);

  if (!isOpen || !proposal) return null;

  // 1. Download Markdown (.md)
  const handleDownloadMarkdown = () => {
    const cleanTitle = (proposal.title || 'tradecraft-proposal')
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, '-')
      .replace(/(^-|-$)/g, '');
    const filename = `${cleanTitle}.md`;
    const blob = new Blob([proposal.markdown_content || ''], { type: 'text/markdown;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = filename;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  // 2. Export / Print to PDF
  const handlePrintPDF = () => {
    window.print();
  };

  // 3. Copy to Clipboard
  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(proposal.markdown_content || '');
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy', err);
    }
  };

  // 4. Save edits
  const handleSave = async () => {
    if (!onSaveContent) return;
    setSaving(true);
    try {
      await onSaveContent(proposal.id, editContent);
      setIsEditing(false);
    } catch (err) {
      console.error('Failed to save edit', err);
    } finally {
      setSaving(false);
    }
  };

  const createdDate = proposal.created_at
    ? new Date(proposal.created_at).toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        year: 'numeric',
      })
    : 'Recently';

  // Helper: parse structured sections from 7-section proposal markdown
  const parseSections = (mdText) => {
    if (!mdText) return [];
    const lines = mdText.split('\n');
    const sections = [];
    let currentSection = null;

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const headingMatch = line.match(/^##\s+(\d+)\.\s+(.*)$/);

      if (headingMatch) {
        if (currentSection) {
          sections.push(currentSection);
        }
        currentSection = {
          number: headingMatch[1],
          title: headingMatch[2],
          content: [],
        };
      } else if (line.startsWith('# ')) {
        // Document H1 title line, ignore or use
      } else if (currentSection) {
        currentSection.content.push(line);
      } else if (line.trim()) {
        // Pre-section intro
        if (!sections.length && !currentSection) {
          currentSection = {
            number: '0',
            title: 'Overview',
            content: [line],
          };
        }
      }
    }
    if (currentSection) {
      sections.push(currentSection);
    }

    return sections;
  };

  const sections = parseSections(proposal.markdown_content);

  // Render formatted lines within a section
  const renderSectionContent = (contentLines) => {
    const text = contentLines.join('\n').trim();
    if (!text) return null;

    // Split paragraphs and blockquotes
    const blocks = text.split('\n\n');

    return (
      <div className="space-y-3.5">
        {blocks.map((block, idx) => {
          const trimmed = block.trim();
          if (!trimmed) return null;

          // Blockquote (Evidence excerpt)
          if (trimmed.startsWith('>')) {
            const rawQuote = trimmed.replace(/^>\s*/gm, '').trim();
            // Check for Source attribution link: *(Source: [URL](URL))*
            const sourceMatch = rawQuote.match(/\*\(Source:\s*\[(.*?)\]\((.*?)\)\)\*/);
            const quoteOnly = rawQuote.replace(/\*\(Source:.*?\)\*/g, '').replace(/^"|"$/g, '').trim();

            return (
              <div
                key={idx}
                className="relative pl-5 pr-4 py-3.5 rounded-xl border border-primary/25 bg-primary-light/40 dark:bg-primary-bg/20 my-3"
              >
                <div className="flex items-start gap-2.5">
                  <Quote size={18} className="text-primary shrink-0 mt-0.5 opacity-80" />
                  <div className="flex-1 space-y-1.5">
                    <p className="text-xs sm:text-sm font-medium italic text-text leading-relaxed">
                      "{quoteOnly}"
                    </p>
                    {sourceMatch && (
                      <div className="flex items-center gap-1.5 pt-1 text-2xs text-muted">
                        <span className="font-semibold uppercase tracking-wider text-primary">Source:</span>
                        <a
                          href={sourceMatch[2]}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="hover:underline text-primary inline-flex items-center gap-1 font-mono truncate max-w-md"
                        >
                          {sourceMatch[1]}
                          <ExternalLink size={10} />
                        </a>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            );
          }

          // Bullet List
          if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
            const items = trimmed.split('\n').filter((l) => l.trim().startsWith('- ') || l.trim().startsWith('* '));
            return (
              <ul key={idx} className="space-y-1.5 pl-2">
                {items.map((item, itemIdx) => {
                  const itemText = item.replace(/^[-*]\s+/, '');
                  // Bold prefix check (e.g. **Phase 1**: ...)
                  const boldMatch = itemText.match(/^\*\*(.*?)\*\*:(.*)$/);

                  if (boldMatch) {
                    return (
                      <li key={itemIdx} className="text-xs sm:text-sm text-text flex items-start gap-2 leading-relaxed">
                        <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0 mt-2" />
                        <div>
                          <strong className="text-text font-semibold">{boldMatch[1]}:</strong>
                          <span className="text-muted ml-1">{boldMatch[2]}</span>
                        </div>
                      </li>
                    );
                  }

                  return (
                    <li key={itemIdx} className="text-xs sm:text-sm text-text flex items-start gap-2 leading-relaxed">
                      <span className="w-1.5 h-1.5 rounded-full bg-primary shrink-0 mt-2" />
                      <span>{itemText}</span>
                    </li>
                  );
                })}
              </ul>
            );
          }

          // Regular paragraph
          return (
            <p key={idx} className="text-xs sm:text-sm text-text leading-relaxed font-sans">
              {trimmed}
            </p>
          );
        })}
      </div>
    );
  };

  return (
    <div className="glass-overlay" onClick={onClose}>
      <div
        className="glass-panel text-text"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header Bar */}
        <div className="glass-panel-header no-print">
          <div className="glass-panel-header-title">
            <div className="w-9 h-9 rounded-lg bg-primary-light flex items-center justify-center text-primary shrink-0 border border-primary/20 shadow-sm">
              <FileText size={18} />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 min-w-0">
                <h1 className="text-sm sm:text-base font-bold text-text truncate m-0" title={proposal.title}>
                  {proposal.title}
                </h1>
                <Badge variant={proposal.status === 'FINALIZED' ? 'success' : 'neutral'} className="shrink-0 text-2xs">
                  {proposal.status}
                </Badge>
              </div>
              <div className="flex items-center gap-2 text-2xs text-muted mt-0.5 truncate">
                <span className="shrink-0 flex items-center gap-1">
                  <Calendar size={10} /> {createdDate}
                </span>
                {proposal.target_goal && (
                  <span className="text-primary truncate">
                    • <strong>Goal:</strong> {proposal.target_goal}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Action Toolbar */}
          <div className="glass-panel-header-actions">
            {/* Status toggle */}
            {onToggleStatus && (
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onToggleStatus(proposal.id)}
                className="text-xs px-2.5 py-1 whitespace-nowrap"
              >
                {proposal.status === 'FINALIZED' ? 'Draft' : 'Finalize'}
              </Button>
            )}

            {/* Copy Markdown */}
            <Button
              variant="secondary"
              size="sm"
              onClick={handleCopy}
              className="text-xs px-2.5 py-1 whitespace-nowrap"
              title="Copy markdown content to clipboard"
            >
              {copied ? (
                <>
                  <Check size={12} className="mr-1 text-success" />
                  <span className="text-success font-medium">Copied!</span>
                </>
              ) : (
                <>
                  <Copy size={12} className="mr-1" />
                  <span>Copy</span>
                </>
              )}
            </Button>

            {/* Download .md */}
            <Button
              variant="secondary"
              size="sm"
              onClick={handleDownloadMarkdown}
              className="text-xs px-2.5 py-1 whitespace-nowrap"
              title="Download proposal as a Markdown (.md) file"
            >
              <Download size={12} className="mr-1" />
              <span>Download</span>
            </Button>

            {/* Export PDF */}
            <Button
              variant="secondary"
              size="sm"
              onClick={handlePrintPDF}
              className="text-xs px-2.5 py-1 whitespace-nowrap"
              title="Print or Export to PDF"
            >
              <Printer size={12} className="mr-1" />
              <span>PDF</span>
            </Button>

            {/* Edit / View Mode Toggle */}
            {isEditing ? (
              <div className="flex items-center gap-1">
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => setIsEditing(false)}
                  className="text-xs px-2 py-1"
                >
                  Cancel
                </Button>
                <Button
                  variant="primary"
                  size="sm"
                  onClick={handleSave}
                  disabled={saving}
                  className="text-xs px-2.5 py-1"
                >
                  <Save size={12} className="mr-1" />
                  <span>{saving ? 'Saving...' : 'Save'}</span>
                </Button>
              </div>
            ) : (
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setEditContent(proposal.markdown_content || '');
                  setIsEditing(true);
                }}
                className="text-xs px-2.5 py-1 whitespace-nowrap"
              >
                <Edit3 size={12} className="mr-1" />
                <span>Edit</span>
              </Button>
            )}

            {/* Close button */}
            <button
              onClick={onClose}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-muted hover:text-text hover:bg-white/10 dark:hover:bg-white/10 transition-colors ml-1 shrink-0 cursor-pointer"
              title="Close window (Esc)"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Modal Scrollable Body */}
        <div
          className="glass-panel-body glass-scroll"
          style={{
            overflowY: 'scroll',
            scrollBehavior: 'smooth',
            overscrollBehavior: 'contain',
          }}
        >
          {isEditing ? (
            /* Black IDE-grade Edit Mode */
            <div className="space-y-3 h-full flex flex-col">
              <div className="flex items-center justify-between text-xs text-muted">
                <span className="font-semibold text-text">Markdown Source Editor</span>
                <span className="font-mono text-2xs opacity-75">Theme: Pitch Black IDE</span>
              </div>
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                rows={24}
                className="w-full flex-1 font-mono text-xs p-5 rounded-xl outline-none focus:ring-1 focus:ring-primary leading-relaxed shadow-inner"
                style={{
                  backgroundColor: '#000000',
                  color: '#f8fafc',
                  border: '1px solid #262626',
                  minHeight: '480px',
                }}
                placeholder="Enter proposal markdown content..."
              />
            </div>
          ) : (
            /* Executive Glass Document Reader */
            <div className="printable-proposal max-w-4xl mx-auto space-y-8">
              {/* Document Banner */}
              <div className="border-b border-border/60 pb-6 mb-6">
                <div className="flex items-center justify-between text-xs text-muted uppercase tracking-wider mb-2 font-mono">
                  <span>TradeCraft Executive Counter-Proposal</span>
                  <span>Standard 7-Section Framework</span>
                </div>
                <h1 className="text-2xl sm:text-3xl font-extrabold text-text tracking-tight mb-2">
                  {proposal.title}
                </h1>
                {proposal.target_goal && (
                  <p className="text-sm text-primary font-medium flex items-center gap-1.5">
                    <Target size={15} />
                    <span>Strategic Objective: {proposal.target_goal}</span>
                  </p>
                )}
              </div>

              {/* 7 Structured Sections */}
              {sections.length > 0 ? (
                sections.map((sec, secIdx) => (
                  <section
                    key={secIdx}
                    className="p-5 sm:p-6 rounded-2xl bg-surface/50 dark:bg-surface/30 border border-border/70 shadow-sm space-y-3.5 backdrop-blur-sm"
                  >
                    <div className="flex items-center gap-3 pb-2 border-b border-border/40">
                      <span className="w-7 h-7 rounded-lg bg-primary text-white text-xs font-bold flex items-center justify-center shrink-0 shadow-sm">
                        {sec.number !== '0' ? sec.number : '•'}
                      </span>
                      <h2 className="text-base sm:text-lg font-bold text-text m-0 tracking-tight">
                        {sec.title}
                      </h2>
                    </div>
                    {renderSectionContent(sec.content)}
                  </section>
                ))
              ) : (
                /* Fallback unstructured markdown display */
                <div className="p-6 rounded-2xl bg-surface/50 border border-border text-xs leading-relaxed whitespace-pre-wrap font-sans text-text">
                  {proposal.markdown_content}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
