import { useEffect, useState } from 'react';
import client from '../api/client';
import StatusBadge from '../components/StatusBadge';

const STATUSES = ['draft', 'submitted', 'won', 'lost'];

export default function ProposalsPage() {
  const [proposals, setProposals] = useState([]);
  const [total, setTotal] = useState(0);
  const [filter, setFilter] = useState('');
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 50;

  const load = async () => {
    try {
      const params = { page, page_size: PAGE_SIZE };
      if (filter) params.status = filter;
      const res = await client.get('/proposals', { params });
      setProposals(res.data.items);
      setTotal(res.data.total);
    } catch (e) {
      console.error('Failed to load proposals:', e.message);
    }
  };

  useEffect(() => { load(); }, [filter, page]);

  const downloadProposal = async (id) => {
    const res = await fetch(`/api/proposals/${id}/download`);
    const fallback = res.headers.get('X-Fallback-Format');
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = fallback === 'docx' ? `proposal_${id}.docx` : `proposal_${id}.pdf`;
    a.click();
    URL.revokeObjectURL(url);
    if (fallback === 'docx') {
      alert('PDF conversion unavailable — downloading as Word document.');
    }
  };

  const updateStatus = async (id, status) => {
    await client.put(`/proposals/${id}`, { status });
    load();
  };

  const del = async (id) => {
    if (!confirm('Delete this proposal?')) return;
    await client.delete(`/proposals/${id}`);
    load();
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
            {['Tender', 'Template', 'Created', 'Status', 'Actions'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: '#888' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {proposals.map(p => (
            <tr key={p.id} style={{ borderBottom: '1px solid #222' }}>
              <td style={{ padding: '10px 12px' }}>{p.tender_title}</td>
              <td style={{ padding: '10px 12px', color: '#888' }}>{p.template_name || '(deleted)'}</td>
              <td style={{ padding: '10px 12px', color: '#888', fontSize: 13 }}>{new Date(p.created_at).toLocaleDateString()}</td>
              <td style={{ padding: '10px 12px' }}>
                <select value={p.status} onChange={e => updateStatus(p.id, e.target.value)} style={{ background: '#1e1e2e', border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, padding: '2px 6px' }}>
                  {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
                </select>
              </td>
              <td style={{ padding: '10px 12px' }}>
                <button onClick={() => downloadProposal(p.id)} style={{ color: '#a89cf7', background: 'none', border: 'none', cursor: 'pointer', marginRight: 12, fontSize: 13 }}>Download</button>
                <button onClick={() => del(p.id)} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <button disabled={page === 1} onClick={() => setPage(p => p - 1)}>Prev</button>
        <span>Page {page} of {Math.ceil(total / PAGE_SIZE) || 1}</span>
        <button disabled={page * PAGE_SIZE >= total} onClick={() => setPage(p => p + 1)}>Next</button>
      </div>
    </div>
  );
}
