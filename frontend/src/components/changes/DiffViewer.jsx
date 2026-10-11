// frontend/src/components/changes/DiffViewer.jsx
// Syntax-highlighted unified diff viewer for Phase 4 Change Detection

export default function DiffViewer({ diffUnified }) {
  if (!diffUnified) {
    return (
      <div className="text-muted text-sm p-4 text-center">No diff available.</div>
    );
  }

  const lines = diffUnified.split('\n');

  return (
    <div style={{
      fontFamily: 'monospace',
      fontSize: '13px',
      background: 'var(--bg)',
      border: '1px solid var(--border)',
      borderRadius: 'var(--radius)',
      overflowX: 'auto',
      maxHeight: '420px',
      overflowY: 'auto',
    }}>
      <table style={{ borderCollapse: 'collapse', width: '100%', minWidth: '600px' }}>
        <tbody>
          {lines.map((line, idx) => {
            let bg = 'transparent';
            let color = 'var(--text)';
            let fontWeight = 'normal';

            if (line.startsWith('+++') || line.startsWith('---')) {
              bg = 'var(--primary-bg)';
              color = 'var(--primary)';
              fontWeight = '600';
            } else if (line.startsWith('@@')) {
              bg = 'var(--purple-bg)';
              color = 'var(--purple)';
              fontWeight = '600';
            } else if (line.startsWith('+')) {
              bg = 'var(--success-bg)';
              color = 'var(--success)';
            } else if (line.startsWith('-')) {
              bg = 'var(--danger-bg)';
              color = 'var(--danger)';
            } else {
              color = 'var(--muted)';
            }

            return (
              <tr key={idx} style={{ background: bg }}>
                <td style={{
                  padding: '1px 8px',
                  userSelect: 'none',
                  color: 'var(--muted)',
                  textAlign: 'right',
                  minWidth: '40px',
                  borderRight: '1px solid var(--border)',
                  fontSize: '11px',
                }}>
                  {idx + 1}
                </td>
                <td style={{
                  padding: '1px 12px',
                  whiteSpace: 'pre',
                  color,
                  fontWeight,
                }}>
                  {line || ' '}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
