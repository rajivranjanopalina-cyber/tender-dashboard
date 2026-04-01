import { useEffect, useState, useRef } from 'react';
import client from '../api/client';
import StatusBadge from '../components/StatusBadge';
import TenderDetail from '../components/TenderDetail';
import ConfirmDialog from '../components/ConfirmDialog';
import { useToast } from '../components/Toast';

export default function Dashboard() {
  const toast = useToast();
  const [tenders, setTenders] = useState([]);
  const [total, setTotal] = useState(0);
  const [stats, setStats] = useState({ total: 0, newSinceLast: 0, approved: 0, underReview: 0, rejected: 0 });
  const [filters, setFilters] = useState({ status: '', keyword: '', portal_id: '', date_from: '', date_to: '' });
  const [portals, setPortals] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [confirm, setConfirm] = useState(null);
  const pollRef = useRef(null);
  const PAGE_SIZE = 50;

  const load = async () => {
    setLoading(true);
    try {
      const params = { page, page_size: PAGE_SIZE };
      if (filters.status) params.status = filters.status;
      if (filters.keyword) params.keyword = filters.keyword;
      if (filters.portal_id) params.portal_id = filters.portal_id;
      if (filters.date_from) params.date_from = filters.date_from;
      if (filters.date_to) params.date_to = filters.date_to;
      const res = await client.get('/tenders', { params });
      setTenders(res.data.items);
      setTotal(res.data.total);
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    try {
      const [all, approved, underReview, rejected, logs] = await Promise.all([
        client.get('/tenders', { params: { page_size: 1 } }),
        client.get('/tenders', { params: { status: 'approved', page_size: 1 } }),
        client.get('/tenders', { params: { status: 'under_review', page_size: 1 } }),
        client.get('/tenders', { params: { status: 'rejected', page_size: 1 } }),
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
        rejected: rejected.data.total,
      });
    } catch (e) {
      console.error('Failed to load stats:', e.message);
    }
  };

  const pollScrapeStatus = async () => {
    try {
      const res = await client.get('/scraper/status');
      if (res.data.is_running) {
        if (!pollRef.current) {
          pollRef.current = setInterval(async () => {
            const s = await client.get('/scraper/status');
            if (!s.data.is_running) {
              clearInterval(pollRef.current);
              pollRef.current = null;
              load();
              loadStats();
            }
          }, 10000);
        }
      }
    } catch {}
  };

  useEffect(() => {
    loadStats();
    pollScrapeStatus();
    client.get('/portals').then(r => setPortals(r.data.items)).catch(() => {});
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, []);
  useEffect(() => { load(); }, [filters, page]);

  const handleStatusChange = (id, status) => {
    const label = status === 'approved' ? 'Approve' : 'Reject';
    setConfirm({
      title: `${label} Tender`,
      message: `Are you sure you want to ${label.toLowerCase()} this tender?`,
      onConfirm: async () => {
        setConfirm(null);
        try {
          await client.put(`/tenders/${id}`, { status });
          toast(`Tender ${label.toLowerCase()}d`, 'success');
          load();
          loadStats();
        } catch (e) { toast(e.message, 'error'); }
      },
    });
  };

  return (
    <div>
      <h2>Dashboard</h2>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 24, flexWrap: 'wrap' }}>
        {[
          ['Total Tenders', stats.total, '#a89cf7'],
          ['New Since Last Scrape', stats.newSinceLast, '#10b981'],
          ['Approved', stats.approved, '#52c41a'],
          ['Under Review', stats.underReview, '#faad14'],
          ['Rejected', stats.rejected, '#ef4444'],
        ].map(([label, val, color]) => (
          <div key={label} style={{ background: '#1e1e2e', borderRadius: 8, padding: '16px 24px', flex: 1, minWidth: 140 }}>
            <div style={{ fontSize: 28, fontWeight: 700, color }}>{val}</div>
            <div style={{ color: '#888', fontSize: 13 }}>{label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <select value={filters.status} onChange={e => { setFilters(f => ({ ...f, status: e.target.value })); setPage(1); }}>
          <option value="">All Statuses</option>
          <option value="new">New</option>
          <option value="under_review">Under Review</option>
          <option value="approved">Approved</option>
          <option value="rejected">Rejected</option>
        </select>
        <select value={filters.portal_id} onChange={e => { setFilters(f => ({ ...f, portal_id: e.target.value })); setPage(1); }}>
          <option value="">All Portals</option>
          {portals.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <input
          placeholder="Filter by keyword..."
          value={filters.keyword}
          onChange={e => { setFilters(f => ({ ...f, keyword: e.target.value })); setPage(1); }}
        />
        <input
          type="date"
          value={filters.date_from}
          onChange={e => { setFilters(f => ({ ...f, date_from: e.target.value })); setPage(1); }}
          title="From date"
          style={{ background: '#1e1e2e', border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, padding: '4px 8px' }}
        />
        <input
          type="date"
          value={filters.date_to}
          onChange={e => { setFilters(f => ({ ...f, date_to: e.target.value })); setPage(1); }}
          title="To date"
          style={{ background: '#1e1e2e', border: '1px solid #333', color: '#e0e0e0', borderRadius: 4, padding: '4px 8px' }}
        />
      </div>

      {loading && <div style={{ color: '#888', marginBottom: 12 }}>Loading...</div>}

      {/* Table */}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #333' }}>
            {['Title', 'Portal', 'Deadline', 'Value', 'Status', 'Actions'].map(h => (
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
              <td style={{ padding: '10px 12px', color: '#888', fontSize: 13 }}>{t.portal_name}</td>
              <td style={{ padding: '10px 12px' }}>{t.deadline || '—'}</td>
              <td style={{ padding: '10px 12px' }}>{t.estimated_value || '—'}</td>
              <td style={{ padding: '10px 12px' }}><StatusBadge status={t.status} /></td>
              <td style={{ padding: '10px 12px', whiteSpace: 'nowrap' }}>
                {t.status !== 'approved' && (
                  <button onClick={() => handleStatusChange(t.id, 'approved')} style={{ marginRight: 8, color: '#10b981', background: 'none', border: 'none', cursor: 'pointer', fontSize: 13 }}>Approve</button>
                )}
                {t.status !== 'rejected' && (
                  <button onClick={() => handleStatusChange(t.id, 'rejected')} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer', fontSize: 13 }}>Reject</button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {!loading && tenders.length === 0 && (
        <div style={{ textAlign: 'center', color: '#555', padding: '2rem' }}>No tenders found.</div>
      )}

      {/* Pagination */}
      <div style={{ marginTop: 16, display: 'flex', gap: 8 }}>
        <button disabled={page === 1} onClick={() => setPage(p => p - 1)}>Prev</button>
        <span>Page {page} of {Math.ceil(total / PAGE_SIZE) || 1}</span>
        <button disabled={page * PAGE_SIZE >= total} onClick={() => setPage(p => p + 1)}>Next</button>
      </div>

      {selectedId && <TenderDetail tenderId={selectedId} onClose={() => { setSelectedId(null); load(); }} />}
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
