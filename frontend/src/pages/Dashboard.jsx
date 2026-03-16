import { useEffect, useState } from 'react';
import client from '../api/client';
import StatusBadge from '../components/StatusBadge';
import TenderDetail from '../components/TenderDetail';

export default function Dashboard() {
  const [tenders, setTenders] = useState([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState({ total: 0, newSinceLast: 0, approved: 0, underReview: 0 });
  const [filters, setFilters] = useState({ status: '', keyword: '' });
  const [selectedId, setSelectedId] = useState(null);
  const [page, setPage] = useState(1);
  const PAGE_SIZE = 50;

  const load = async () => {
    try {
      const params = { page, page_size: PAGE_SIZE };
      if (filters.status) params.status = filters.status;
      if (filters.keyword) params.keyword = filters.keyword;
      const res = await client.get('/tenders', { params });
      setTenders(res.data.items);
      setTotal(res.data.total);
    } catch (e) {
      console.error('Failed to load tenders:', e.message);
    }
  };

  const loadStats = async () => {
    try {
      const [all, approved, underReview, logs] = await Promise.all([
        client.get('/tenders', { params: { page_size: 1 } }),
        client.get('/tenders', { params: { status: 'approved', page_size: 1 } }),
        client.get('/tenders', { params: { status: 'under_review', page_size: 1 } }),
        client.get('/scraper/logs', { params: { page_size: 1 } }),
      ]);
      const lastRun = logs.data.items[0]?.run_at;
      let newSinceLast = 0;
      if (lastRun) {
        const res = await client.get('/tenders', { params: { scraped_from: lastRun, page_size: 1 } });
        newSinceLast = res.data.total;
      }
      setStats({
        total: all.data.total,
        newSinceLast,
        approved: approved.data.total,
        underReview: underReview.data.total,
      });
    } catch (e) {
      console.error('Failed to load stats:', e.message);
    }
  };

  // Stats reflect global counts — only reload on mount, not on every filter/page change
  useEffect(() => { loadStats(); }, []);
  useEffect(() => { load(); }, [filters, page]);

  const handleApprove = async (id) => {
    await client.put(`/tenders/${id}`, { status: 'approved' });
    load();
  };

  const handleReject = async (id) => {
    await client.put(`/tenders/${id}`, { status: 'rejected' });
    load();
  };

  return (
    <div>
      <h2>Dashboard</h2>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24 }}>
        {[
          ['Total Tenders', stats.total],
          ['New Since Last Scrape', stats.newSinceLast],
          ['Approved', stats.approved],
          ['Under Review', stats.underReview],
        ].map(([label, val]) => (
          <div key={label} style={{ background: '#1e1e2e', borderRadius: 8, padding: '16px 24px', flex: 1 }}>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{val}</div>
            <div style={{ color: '#888', fontSize: 13 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16 }}>
        <select value={filters.status} onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}>
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="under_review">Under Review</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
        <input
          placeholder="Filter by keyword..."
          value={filters.keyword}
          onChange={e => setFilters(f => ({ ...f, keyword: e.target.value }))}
        />
      </div>

      {/* Table */}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #333' }}>
            {['Title', 'Source', 'Deadline', 'Value', 'Status', 'Actions'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: '#888' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {tenders.map(t => (
            <tr key={t.id} style={{ borderBottom: '1px solid #222' }}>
              <td style={{ padding: '10px 12px' }}>
                <button onClick={() => setSelectedId(t.id)} style={{ background: 'none', border: 'none', color: '#a89cf7', cursor: 'pointer', textAlign: 'left', padding: 0 }}>
                  {t.title}
                </button>
              </td>
              <td style={{ padding: '10px 12px', color: '#888' }}>{t.portal_name}</td>
              <td style={{ padding: '10px 12px' }}>{t.deadline || '—'}</td>
              <td style={{ padding: '10px 12px' }}>{t.estimated_value || '—'}</td>
              <td style={{ padding: '10px 12px' }}><StatusBadge status={t.status} /></td>
              <td style={{ padding: '10px 12px' }}>
                <button onClick={() => handleApprove(t.id)} style={{ marginRight: 8, color: '#10b981', background: 'none', border: 'none', cursor: 'pointer' }}>Approve</button>
                <button onClick={() => handleReject(t.id)} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}>Reject</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {/* Pagination */}
      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <button disabled={page === 1} onClick={() => setPage(p => p - 1)}>Prev</button>
        <span>Page {page} of {Math.ceil(total / PAGE_SIZE) || 1}</span>
        <button disabled={page * PAGE_SIZE >= total} onClick={() => setPage(p => p + 1)}>Next</button>
      </div>

      {selectedId && <TenderDetail tenderId={selectedId} onClose={() => { setSelectedId(null); load(); }} />}
    </div>
  );
}
