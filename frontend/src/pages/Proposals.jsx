import { useEffect, useState } from 'react';
import client from '../api/client';
import StatusBadge from '../components/StatusBadge';
import ConfirmDialog from '../components/ConfirmDialog';
import { useToast } from '../components/Toast';

const STATUSES = ['draft', 'submitted', 'won', 'lost'];

const PIPELINE = [
  { status: 'draft', label: 'Draft' },
  { status: 'submitted', label: 'Submitted' },
  { status: 'won', label: 'Won' },
  { status: 'lost', label: 'Lost' },
];

function PipelineIndicator({ current }) {
  const idx = PIPELINE.findIndex(s => s.status === current);
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: 11 }}>
      {PIPELINE.map((s, i) => (
        <div key={s.status} style={{ display: 'flex', alignItems: 'center' }}>
          <div style={{
            padding: '2px 8px', borderRadius: 10,
            background: i === idx ? '#a89cf7' : i < idx ? '#333' : '#1e1e2e',
            color: i === idx ? '#0d0d1a' : i < idx ? '#666' : '#444',
            fontWeight: i === idx ? 700 : 400,
            border: `1px solid ${i === idx ? '#a89cf7' : '#333'}`,
          }}>
            {s.label}
          </div>
          {i < PIPELINE.length - 1 && <div style={{ width: 12, height: 1, background: '#333', margin: '0 2px' }} />}
        </div>
      ))}
    </div>
  );
}

export default function ProposalsPage() {
  const toast = useToast();
  const [proposals, setProposals] = useState([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState('');
  const [page, setPage] = useState(1);
  const [confirm, setConfirm] = useState(null);
  const PAGE_SIZE = 50;

  const load = async () => {
    try {
      const params = { page, page_size: PAGE_SIZE };
      if (filter) params.status = filter;
      const res = await client.get('/proposals', { params });
      setProposals(res.data.items);
      setTotal(res.data.total);
    } catch (e) {
      toast(e.message, 'error');
    }
  };

  useEffect(() => { load(); }, [filter, page]);

  const downloadProposal = async (p) => {
    if (p.blob_url) {
      window.open(p.blob_url, '_blank');
      return;
    }
    const token = localStorage.getItem('token');
    const res = await fetch(`/api/proposals/${p.id}/download`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    });
    const fallback = res.headers.get('X-Fallback-Format');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fallback === 'docx' ? `proposal_${p.id}.docx` : `proposal_${p.id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
    if (fallback === 'docx') {
      toast('PDF conversion unavailable — downloading as Word document.', 'info');
    }
  };

  const updateStatus = async (id, status) => {
    try {
      await client.put(`/proposals/${id}`, { status });
      toast(`Status updated to ${status}`, 'success');
      load();
    } catch (e) { toast(e.message, 'error'); }
  };

  const del = (id) => {
    setConfirm({
      title: 'Delete Proposal',
      message: 'Delete this proposal? This cannot be undone.',
      onConfirm: async () => {
        setConfirm(null);
        try {
          await client.delete(`/proposals/${id}`);
          toast('Proposal deleted', 'success');
          load();
        } catch (e) { toast(e.message, 'error'); }
      },
    });
  };

  return (
    <div>
      <h2>Proposals</h2>

      <div style={{ marginBottom: 16 }}>
        <select value={filter} onChange={e => { setFilter(e.target.value); setPage(1); }}>
          <option value="">All Statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #333' }}>
            {['Tender', 'Template', 'Pipeline', 'Created', 'Status', 'Actions'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: '#888' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {proposals.map(p => (
            <tr key={p.id} style={{ borderBottom: '1px solid #222' }}>
              <td style={{ padding: '10px 12px', maxWidth: 200, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                <span title={p.tender_title} style={{ color: '#a89cf7', fontSize: 13 }}>{p.tender_title}</span>
              </td>
              <td style={{ padding: '10px 12px', color: '#888', fontSize: 13 }}>{p.template_name || '(deleted)'}</td>
              <td style={{ padding: '10px 12px' }}>
                <PipelineIndicator current={p.status} />
              </td>
              <td style={{ padding: '10px 12px', color: '#888', fontSize: 13 }}>{new Date(p.created_at).toLocaleDateString()}</td>
              <td style={{ padding: '10px 12px' }}>
                <select
                  value={p.status}
                  onChange={e => updateStatus(p.id, e.target.value)}
                  style={{ background: '#1e1e2e', border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, padding: '2px 6px' }}
                >
                  {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </td>
              <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                <button onClick={() => downloadProposal(p)} style={{ color: '#a89cf7', background: 'none', border: 'none', cursor: 'pointer', marginRight: 12, fontSize: 13 }}>Download</button>
                <button onClick={() => del(p.id)} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {proposals.length === 0 && (
        <div style={{ textAlign: 'center', color: '#555', padding: '2rem' }}>No proposals found.</div>
      )}

      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <button disabled={page === 1} onClick={() => setPage(p => p - 1)}>Prev</button>
        <span>Page {page} of {Math.ceil(total / PAGE_SIZE) || 1}</span>
        <button disabled={page * PAGE_SIZE >= total} onClick={() => setPage(p => p + 1)}>Next</button>
      </div>

      {confirm && (
        <ConfirmDialog
          open
          title={confirm.title}
          message={confirm.message}
          onConfirm={confirm.onConfirm}
          onCancel={() => setConfirm(null)}
        />
      )}
    </div>
  );
}
