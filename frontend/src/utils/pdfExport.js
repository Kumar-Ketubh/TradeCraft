// frontend/src/utils/pdfExport.js
/**
 * Utility to export TradeCraft Proposals to a clean, executive-ready PDF.
 * Uses an isolated, off-screen print iframe to guarantee zero clipping,
 * correct pagination, and complete immunity from dark-mode styles or modal overflow traps.
 */

function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

function parseMarkdownToHtml(mdText) {
  if (!mdText) return '';

  const lines = mdText.split('\n');
  const sections = [];
  let currentSection = null;
  const preSectionIntro = [];

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
      // Top-level document title (already rendered in header)
    } else if (currentSection) {
      currentSection.content.push(line);
    } else if (line.trim()) {
      preSectionIntro.push(line);
    }
  }

  if (currentSection) {
    sections.push(currentSection);
  }

  // Helper to format body blocks
  const formatBlocks = (contentLines) => {
    const text = contentLines.join('\n').trim();
    if (!text) return '';

    const blocks = text.split('\n\n');
    let html = '';

    for (const block of blocks) {
      const trimmed = block.trim();
      if (!trimmed) continue;

      // Blockquote (Evidence excerpt)
      if (trimmed.startsWith('>')) {
        const rawQuote = trimmed.replace(/^>\s*/gm, '').trim();
        const sourceMatch = rawQuote.match(/\*\(Source:\s*\[(.*?)\]\((.*?)\)\)\*/);
        const quoteOnly = rawQuote.replace(/\*\(Source:.*?\)\*/g, '').replace(/^"|"$/g, '').trim();

        html += `
          <div class="evidence-quote">
            <div class="quote-text">“${escapeHtml(quoteOnly)}”</div>
            ${
              sourceMatch
                ? `<div class="quote-source"><strong>Source:</strong> <a href="${escapeHtml(
                    sourceMatch[2]
                  )}" target="_blank">${escapeHtml(sourceMatch[1])}</a></div>`
                : ''
            }
          </div>
        `;
        continue;
      }

      // Bullet lists
      if (trimmed.startsWith('- ') || trimmed.startsWith('* ')) {
        const items = trimmed
          .split('\n')
          .filter((l) => l.trim().startsWith('- ') || l.trim().startsWith('* '));
        html += '<ul class="bullet-list">';
        for (const item of items) {
          const itemText = item.replace(/^[-*]\s+/, '');
          const boldMatch = itemText.match(/^\*\*(.*?)\*\*:(.*)$/);
          if (boldMatch) {
            html += `<li><strong>${escapeHtml(boldMatch[1])}:</strong> <span>${escapeHtml(
              boldMatch[2]
            )}</span></li>`;
          } else {
            const formatted = escapeHtml(itemText).replace(
              /\*\*(.*?)\*\*/g,
              '<strong>$1</strong>'
            );
            html += `<li>${formatted}</li>`;
          }
        }
        html += '</ul>';
        continue;
      }

      // Paragraph
      const formatted = escapeHtml(trimmed).replace(
        /\*\*(.*?)\*\*/g,
        '<strong>$1</strong>'
      );
      html += `<p class="paragraph">${formatted}</p>`;
    }

    return html;
  };

  let outputHtml = '';

  if (preSectionIntro.length > 0) {
    outputHtml += `<div class="pre-intro">${formatBlocks(preSectionIntro)}</div>`;
  }

  if (sections.length > 0) {
    for (const sec of sections) {
      outputHtml += `
        <div class="section-card">
          <div class="section-header">
            <span class="section-number">${escapeHtml(sec.number)}</span>
            <h2 class="section-title">${escapeHtml(sec.title)}</h2>
          </div>
          <div class="section-body">
            ${formatBlocks(sec.content)}
          </div>
        </div>
      `;
    }
  } else {
    outputHtml += `<div class="section-card"><div class="section-body" style="white-space: pre-wrap;">${escapeHtml(
      mdText
    )}</div></div>`;
  }

  return outputHtml;
}

export function exportProposalToPDF(proposal) {
  if (!proposal) return;

  const title = proposal.title || 'TradeCraft Executive Proposal';
  const targetGoal = proposal.target_goal || '';
  const status = proposal.status || 'DRAFT';
  const createdDate = proposal.created_at
    ? new Date(proposal.created_at).toLocaleDateString('en-US', {
        month: 'long',
        day: 'numeric',
        year: 'numeric',
      })
    : 'Recent';

  const bodyHtml = parseMarkdownToHtml(proposal.markdown_content || '');

  const printDocumentHtml = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>${escapeHtml(title)} - TradeCraft Proposal</title>
  <style>
    @page {
      size: letter;
      margin: 18mm 16mm 18mm 16mm;
    }
    * {
      box-sizing: border-box;
      -webkit-print-color-adjust: exact !important;
      print-color-adjust: exact !important;
    }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      color: #0f172a;
      background: #ffffff !important;
      margin: 0;
      padding: 0;
      font-size: 13px;
      line-height: 1.6;
    }
    .header-bar {
      border-bottom: 2px solid #0f172a;
      padding-bottom: 14px;
      margin-bottom: 24px;
    }
    .meta-top {
      display: flex;
      justify-content: space-between;
      align-items: center;
      font-size: 10px;
      font-weight: 700;
      text-transform: uppercase;
      letter-spacing: 0.1em;
      color: #2563eb;
      margin-bottom: 8px;
    }
    .proposal-title {
      font-size: 24px;
      font-weight: 800;
      line-height: 1.25;
      color: #0f172a;
      margin: 0 0 10px 0;
      letter-spacing: -0.02em;
    }
    .meta-sub {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 16px;
      font-size: 11px;
      color: #475569;
    }
    .badge {
      display: inline-block;
      padding: 2px 8px;
      font-size: 10px;
      font-weight: 700;
      border-radius: 4px;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
    .badge-finalized {
      background: #dcfce7;
      color: #166534;
      border: 1px solid #bbf7d0;
    }
    .badge-draft {
      background: #f1f5f9;
      color: #475569;
      border: 1px solid #e2e8f0;
    }
    .goal-text {
      color: #1d4ed8;
      font-weight: 600;
    }
    .section-card {
      break-inside: avoid;
      page-break-inside: avoid;
      margin-bottom: 18px;
      padding: 16px 18px;
      border: 1px solid #e2e8f0;
      border-radius: 8px;
      background: #ffffff;
    }
    .section-header {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 12px;
      border-bottom: 1px solid #f1f5f9;
      padding-bottom: 8px;
    }
    .section-number {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 22px;
      height: 22px;
      background: #2563eb;
      color: #ffffff;
      font-size: 11px;
      font-weight: 700;
      border-radius: 4px;
    }
    .section-title {
      font-size: 14px;
      font-weight: 700;
      color: #0f172a;
      margin: 0;
      letter-spacing: -0.01em;
    }
    .section-body {
      font-size: 12px;
      color: #334155;
    }
    .paragraph {
      margin: 0 0 10px 0;
      line-height: 1.6;
    }
    .paragraph:last-child {
      margin-bottom: 0;
    }
    .evidence-quote {
      margin: 10px 0;
      padding: 10px 14px;
      background: #f8fafc;
      border-left: 3px solid #2563eb;
      border-radius: 0 6px 6px 0;
    }
    .quote-text {
      font-style: italic;
      color: #1e293b;
      font-weight: 500;
      margin-bottom: 4px;
    }
    .quote-source {
      font-size: 10px;
      color: #64748b;
    }
    .quote-source a {
      color: #2563eb;
      text-decoration: underline;
    }
    .bullet-list {
      margin: 8px 0;
      padding-left: 18px;
    }
    .bullet-list li {
      margin-bottom: 6px;
      line-height: 1.5;
    }
    .footer-bar {
      margin-top: 30px;
      padding-top: 12px;
      border-top: 1px solid #e2e8f0;
      display: flex;
      justify-content: space-between;
      font-size: 9px;
      color: #94a3b8;
      text-transform: uppercase;
      letter-spacing: 0.05em;
    }
  </style>
</head>
<body>
  <div class="header-bar">
    <div class="meta-top">
      <span>TradeCraft Autonomous Competitive Intelligence</span>
      <span>Executive Strategic Counter-Proposal</span>
    </div>
    <h1 class="proposal-title">${escapeHtml(title)}</h1>
    <div class="meta-sub">
      <span class="badge ${status === 'FINALIZED' ? 'badge-finalized' : 'badge-draft'}">${escapeHtml(status)}</span>
      <span><strong>Date:</strong> ${escapeHtml(createdDate)}</span>
      ${
        targetGoal
          ? `<span class="goal-text"><strong>Objective:</strong> ${escapeHtml(targetGoal)}</span>`
          : ''
      }
    </div>
  </div>

  <div class="content-container">
    ${bodyHtml}
  </div>

  <div class="footer-bar">
    <span>TradeCraft Strategic Synthesis Engine • Strictly Confidential</span>
    <span>7-Section Executive Framework</span>
  </div>
</body>
</html>`;

  // Create an isolated invisible iframe to avoid dark mode or viewport clipping
  const iframe = document.createElement('iframe');
  iframe.style.position = 'fixed';
  iframe.style.right = '0';
  iframe.style.bottom = '0';
  iframe.style.width = '0';
  iframe.style.height = '0';
  iframe.style.border = '0';
  iframe.setAttribute('aria-hidden', 'true');
  document.body.appendChild(iframe);

  const doc = iframe.contentWindow.document;
  doc.open();
  doc.write(printDocumentHtml);
  doc.close();

  // Allow styles and DOM layout to compute, then trigger native print dialog
  setTimeout(() => {
    try {
      iframe.contentWindow.focus();
      iframe.contentWindow.print();
    } catch (err) {
      console.error('Failed to print proposal PDF:', err);
    } finally {
      setTimeout(() => {
        if (document.body.contains(iframe)) {
          document.body.removeChild(iframe);
        }
      }, 2500);
    }
  }, 250);
}
