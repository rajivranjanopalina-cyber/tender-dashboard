import { useEffect, useRef } from 'react';

export default function ConfirmDialog({ open, title, message, onConfirm, onCancel }) {
  const dialogRef = useRef(null);

  useEffect(() => {
    if (open) dialogRef.current?.focus();
  }, [open]);

  if (!open) return null;

  return (
    <div
      ref={dialogRef}
      tabIndex={-1}
      onKeyDown={(e) => e.key === 'Escape' && onCancel()}
      style={{
        position: 'fixed', inset: 0, zIndex: 10000,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        background: 'rgba(0,0,0,0.6)',
      }}
    >
      <div style={{
        background: '#1a1a2e', borderRadius: '12px', padding: '1.5rem',
        maxWidth: '400px', width: '90%', boxShadow: '0 4px 24px rgba(0,0,0,0.4)',
      }}>
        <h3 style={{ margin: '0 0 0.75rem', color: '#e0e0e0' }}>{title || 'Confirm'}</h3>
        <p style={{ color: '#aaa', fontSize: '0.9rem', margin: '0 0 1.5rem' }}>{message}</p>
        <div style={{ display: 'flex', gap: '0.75rem', justifyContent: 'flex-end' }}>
          <button
            onClick={onCancel}
            style={{
              padding: '0.5rem 1rem', borderRadius: '6px', border: '1px solid #333',
              background: 'transparent', color: '#e0e0e0', cursor: 'pointer',
            }}
          >Cancel</button>
          <button
            onClick={onConfirm}
            style={{
              padding: '0.5rem 1rem', borderRadius: '6px', border: 'none',
              background: '#a89cf7', color: '#0d0d1a', cursor: 'pointer', fontWeight: 600,
            }}
          >Confirm</button>
        </div>
      </div>
    </div>
  );
}
