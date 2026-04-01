import { useEffect, useState } from 'react';
import client from '../api/client';
import StatusBadge from '../components/StatusBadge';
import ScrapeConfigEditor from '../components/ScrapeConfigEditor';
import ConfirmDialog from '../components/ConfirmDialog';
import { useToast } from '../components/Toast';

const DEFAULT_CONFIG = JSON.stringify({
  list_selector: '',
  fields: { title: '', source_url: '' },
  next_button: '',
  date_format: '',
  renderer: 'default',
}, null, 2);

const EMPTY_FORM = { name: '', url: '', requires_auth: false, username: '', password: '', scrape_config: DEFAULT_CONFIG };

export default function ScraperPage() {
  const toast = useToast();
  const [portals, setPortals] = useState([]);
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState({ is_running: false, next_run_at: null });
  const [form, setForm] = useState(EMPTY_FORM);
  const [editing, setEditing] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [expandedLogs, setExpandedLogs] = useState({});
  const [portalLogs, setPortalLogs] = useState({});
  const [running, setRunning] = useState({});
  const [confirm, setConfirm] = useState(null);

  const load = async () => {
    const [p, l, s] = await Promise.all([
      client.get('/portals'),
      client.get('/scraper/logs'),
      client.get('/scraper/status'),
    ]);
    setPortals(p.data.items);
    setLogs(l.data.items);
    setStatus(s.data);
  };

  useEffect(() => { load(); }, []);

  const save = async (e) => {
    e.preventDefault();
    try {
      if (editing) {
        await client.put(`/portals/${editing}`, form);
        toast('Portal updated', 'success');
      } else {
        await client.post('/portals', form);
        toast('Portal added', 'success');
      }
      setForm(EMPTY_FORM);
      setEditing(null);
      setModalOpen(false);
      load();
    } catch (e) { toast(e.message, 'error'); }
  };

  const toggle = async (p) => {
    try {
      await client.put(`/portals/${p.id}`, { enabled: !p.enabled });
      load();
    } catch (e) { toast(e.message, 'error'); }
  };

  const del = (id, name) => {
    setConfirm({
      title: 'Delete Portal',
      message: `Delete portal "${name}"? All associated tenders and scrape logs will be removed.`,
      onConfirm: async () => {
        setConfirm(null);
        try {
          await client.delete(`/portals/${id}`);
          toast('Portal deleted', 'success');
          load();
        } catch (e) { toast(e.message, 'error'); }
      },
    });
  };

  const openEdit = (p) => {
    setEditing(p.id);
    setForm({ name: p.name, url: p.url, requires_auth: p.requires_auth, username: p.username || '', password: '', scrape_config: p.scrape_config || DEFAULT_CONFIG });
    setModalOpen(true);
  };

  const runOne = async (id) => {
    setRunning(r => ({ ...r, [id]: true }));
    try {
      await client.post('/scraper/run', { portal_id: id });
      toast('Scrape started', 'info');
      load();
    } catch (e) { toast(e.message, 'error'); }
    setRunning(r => ({ ...r, [id]: false }));
  };

  const runAll = async () => {
    try {
      await client.post('/scraper/run', { portal_id: null });
      toast('Scraping all portals...', 'info');
      load();
    } catch (e) { toast(e.message, 'error'); }
  };

  const toggleLogs = async (portalId) => {
    const next = !expandedLogs[portalId];
    setExpandedLogs(e => ({ ...e, [portalId]: next }));
    if (next && !portalLogs[portalId]) {
      try {
        const res = await client.get('/scraper/logs', { params: { portal_id: portalId, page_size: 10 } });
        setPortalLogs(l => ({ ...l, [portalId]: res.data.items }));
      } catch {}
    }
  };

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <h2 style={{ margin: 0 }}>Portals & Scraper</h2>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <StatusBadge status={status.is_running ? 'running' : 'idle'} />
          {status.next_run_at && <span style={{ color: '#888', fontSize: 13 }}>Next: {new Date(status.next_run_at).toLocaleString()}</span>}
          <button onClick={runAll} disabled={status.is_running}>Run All</button>
          <button onClick={() => { setEditing(null); setForm(EMPTY_FORM); setModalOpen(true); }} style={{ background: '#a89cf7', color: '#0d0d1a', border: 'none', borderRadius: 6, padding: '6px 14px', cursor: 'pointer', fontWeight: 600 }}>
            + Add Portal
          </button>
        </div>
      </div>

      {/* Portal cards */}
      <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))', marginBottom: 32 }}>
        {portals.map(p => {
          const config = (() => { try { return JSON.parse(p.scrape_config || '{}'); } catch { return {}; } })();
          const isRunning = running[p.id] || status.is_running;
          return (
            <div key={p.id} style={{ background: '#1a1a2e', borderRadius: 10, padding: 16, border: '1px solid #222' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 8 }}>
                <div>
                  <div style={{ fontWeight: 600, color: '#e0e0e0' }}>{p.name}</div>
                  <div style={{ color: '#888', fontSize: 12, marginTop: 2, wordBreak: 'break-all' }}>{p.url}</div>
                </div>
                <div style={{
                  padding: '2px 8px', borderRadius: 10, fontSize: 11, fontWeight: 600,
                  background: p.enabled ? '#10b98122' : '#33333388',
                  color: p.enabled ? '#10b981' : '#666',
                  border: `1px solid ${p.enabled ? '#10b981' : '#444'}`,
                  flexShrink: 0, marginLeft: 8,
                }}>
                  {p.enabled ? 'Enabled' : 'Disabled'}
                </div>
              </div>

              <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#888', marginBottom: 12 }}>
                <span>{config.renderer === 'external' ? 'JS Render' : 'No JS'}</span>
                {p.requires_auth && <span style={{ color: p.has_password ? '#10b981' : '#ef4444' }}>
                  {p.has_password ? '✓ Auth' : '⚠ Auth Required'}
                </span>}
                <span>Last: {p.last_scraped_at ? new Date(p.last_scraped_at).toLocaleDateString() : 'Never'}</span>
              </div>

              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <button onClick={() => toggle(p)} style={{ fontSize: 12, padding: '3px 10px' }}>
                  {p.enabled ? 'Disable' : 'Enable'}
                </button>
                <button onClick={() => openEdit(p)} style={{ fontSize: 12, padding: '3px 10px' }}>Edit</button>
                <button onClick={() => runOne(p.id)} disabled={isRunning} style={{ fontSize: 12, padding: '3px 10px' }}>
                  {isRunning ? 'Running...' : 'Scrape'}
                </button>
                <button onClick={() => toggleLogs(p.id)} style={{ fontSize: 12, padding: '3px 10px', color: '#888' }}>
                  {expandedLogs[p.id] ? 'Hide Logs' : 'Show Logs'}
                </button>
                <button onClick={() => del(p.id, p.name)} style={{ fontSize: 12, padding: '3px 10px', color: '#ef4444', marginLeft: 'auto' }}>Delete</button>
              </div>

              {expandedLogs[p.id] && (
                <div style={{ marginTop: 12, borderTop: '1px solid #222', paddingTop: 10 }}>
                  {(portalLogs[p.id] || []).length === 0
                    ? <div style={{ color: '#555', fontSize: 12 }}>No logs yet.</div>
                    : (portalLogs[p.id] || []).map(l => (
                      <div key={l.id} style={{ fontSize: 11, color: '#888', marginBottom: 4, display: 'flex', gap: 8 }}>
                        <span>{new Date(l.run_at).toLocaleString()}</span>
                        <StatusBadge status={l.status} />
                        <span>{l.tenders_found} found, {l.tenders_new} new</span>
                        {l.error_message && <span style={{ color: '#ef4444' }}>{l.error_message}</span>}
                      </div>
                    ))
                  }
                </div>
              )}
            </div>
          );
        })}
        {portals.length === 0 && (
          <div style={{ color: '#555', gridColumn: '1/-1', textAlign: 'center', padding: '2rem' }}>
            No portals configured. Add one to get started.
          </div>
        )}
      </div>

      {/* Recent scrape logs */}
      <h3>Recent Scrape Activity</h3>
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #333' }}>
            {['Portal', 'Run At', 'Found', 'New', 'Status', 'Error'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: '#888' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {logs.map(l => (
            <tr key={l.id} style={{ borderBottom: '1px solid #222' }}>
              <td style={{ padding: '8px 12px' }}>{l.portal_name}</td>
              <td style={{ padding: '8px 12px', color: '#888', fontSize: 13 }}>{new Date(l.run_at).toLocaleString()}</td>
              <td style={{ padding: '8px 12px' }}>{l.tenders_found}</td>
              <td style={{ padding: '8px 12px' }}>{l.tenders_new}</td>
              <td style={{ padding: '8px 12px' }}><StatusBadge status={l.status} /></td>
              <td style={{ padding: '8px 12px', color: '#ef4444', fontSize: 12 }}>{l.error_message || '—'}</td>
            </tr>
          ))}
          {logs.length === 0 && (
            <tr><td colSpan={6} style={{ padding: '1rem', color: '#555', textAlign: 'center' }}>No scrape activity yet.</td></tr>
          )}
        </tbody>
      </table>

      {/* Add/Edit modal */}
      {modalOpen && (
        <div style={{ position: 'fixed', inset: 0, zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center', background: 'rgba(0,0,0,0.6)' }}>
          <div style={{ background: '#1a1a2e', borderRadius: 12, padding: 24, width: '90%', maxWidth: 600, maxHeight: '90vh', overflowY: 'auto', boxShadow: '0 4px 24px rgba(0,0,0,0.4)' }}>
            <h3 style={{ margin: '0 0 16px', color: '#e0e0e0' }}>{editing ? 'Edit Portal' : 'Add Portal'}</h3>
            <form onSubmit={save}>
              <div style={{ display: 'grid', gap: 12, marginBottom: 16 }}>
                <input required placeholder="Name *" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
                <input required type="url" placeholder="URL *" value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))} />
                <label style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <input type="checkbox" checked={form.requires_auth} onChange={e => setForm(f => ({ ...f, requires_auth: e.target.checked }))} />
                  Requires Authentication
                </label>
                {form.requires_auth && (
                  <>
                    <input placeholder="Username" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} />
                    <input type="password" placeholder={editing ? 'Password (leave blank to keep)' : 'Password'} value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
                  </>
                )}
              </div>
              <div style={{ marginBottom: 16 }}>
                <label style={{ color: '#888', fontSize: 13, marginBottom: 8, display: 'block' }}>Scrape Configuration</label>
                <ScrapeConfigEditor value={form.scrape_config} onChange={val => setForm(f => ({ ...f, scrape_config: val }))} />
              </div>
              <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end' }}>
                <button type="button" onClick={() => { setModalOpen(false); setEditing(null); setForm(EMPTY_FORM); }}>Cancel</button>
                <button type="submit" style={{ background: '#a89cf7', color: '#0d0d1a', border: 'none', borderRadius: 6, padding: '6px 16px', cursor: 'pointer', fontWeight: 600 }}>
                  {editing ? 'Update' : 'Add Portal'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

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
