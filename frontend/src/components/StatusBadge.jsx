const COLORS = {
  new: '#3b82f6',
  under_review: '#f59e0b',
  approved: '#10b981',
  rejected: '#ef4444',
  draft: '#6b7280',
  submitted: '#3b82f6',
  won: '#10b981',
  lost: '#ef4444',
  success: '#10b981',
  failed: '#ef4444',
};

export default function StatusBadge({ status }) {
  const color = COLORS[status] || '#6b7280';
  return (
    <span style={{
      background: color + '22',
      color,
      border: `1px solid ${color}`,
      borderRadius: 4,
      padding: '2px 8px',
      fontSize: 12,
      fontWeight: 600,
      textTransform: 'uppercase',
    }}>
      {status?.replace('_', ' ')}
    </span>
  );
}
