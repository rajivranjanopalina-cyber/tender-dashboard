import { useEffect, useState } from 'react';
import client from '../api/client';
import StatusBadge from '../components/StatusBadge';

const DEFAULT_CONFIG = JSON.stringify({
  render_js: false,
  list_selector: "",
  fields: { title: "", source_url: "" },
  pagination: { type: "none" }
}, null, 2);

export default function ScraperPage() {
  const [portals, setPortals] = useState([]);
  const [logs, setLogs] = useState([]);
  const [status, setStatus] = useState({ is_running: false, next_run_at: null });
  const [form, setForm] = useState({ name: '', url: '', requires_auth: false, username: '', password: '', scrape_config: DEFAULT_CONFIG });
  const [editing, setEditing] = useState(null);
  const [error, setError] = useState('');

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

  const save = async () => {
    setError('');
    try {
      if (editing) {
        await client.put(`/portals/${editing}`, form);
      } else {
        await client.post('/portals', form);
      }
      setForm({ name: '', url: '', requires_auth: false, username: '', password: '', scrape_config: DEFAULT_CONFIG });
      setEditing(null);
      load();
    } catch (e) { setError(e.message); }
  };

  const toggle = async (p) => {
    await client.put(`/portals/${p.id}`, { enabled: !p.enabled });
    load();
  };

  const del = async (id) => {
    if (!confirm('Delete this portal?')) return;
    await client.delete(`/portals/${id}`);
    load();
  };

  const runOne = async (id) => {
    try {
      await client.post('/scraper/run', { portal_id: id });
      load();
    } catch (e) { alert(e.message); }
  };

  const runAll = async () => {
    try {
      await client.post('/scraper/run', { portal_id: null });
      load();
    } catch (e) { alert(e.message); }
  };

  return (
    <div>
      <h2>Scraper</h2>

      <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
        <StatusBadge status={status.is_running ? 'running' : 'idle'} />
        {status.next_run_at && <span style={{ color: '#888', fontSize: 13 }}>Next run: {new Date(status.next_run_at).toLocaleString()}</span>}
        <button onClick={runAll} disabled={status.is_running}>Run All Portals</button>
      </div>

      {/* Portal table */}
      <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 24 }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #333' }}>
            {['Name', 'URL', 'Enabled', 'JS Render', 'Auth', 'Last Scraped', 'Actions'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: '#888' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {portals.map(p => {
            const config = (() => { try { return JSON.parse(p.scrape_config || '{}'); } catch { return {}; } })();
            return (
              <tr key={p.id} style={{ borderBottom: '1px solid #222' }}>
                <td style={{ padding: '10px 12px' }}>{p.name}</td>
                <td style={{ padding: '10px 12px', color: '#888', fontSize: 13 }}>{p.url}</td>
                <td style={{ padding: '10px 12px' }}>
                  <input type="checkbox" checked={p.enabled} onChange={() => toggle(p)} />
                </td>
                <td style={{ padding: '10px 12px', color: config.render_js ? '#10b981' : '#888', fontSize: 13 }}>
                  {config.render_js ? 'Yes' : 'No'}
                </td>
                <td style={{ padding: '10px 12px' }}>
                  {p.requires_auth && !p.has_password
                    ? <span style={{ color: '#ef4444', fontSize: 12, fontWeight: 600 }}>⚠ Auth Required</span>
                    : p.requires_auth ? '✓' : '—'}
                </td>
                <td style={{ padding: '10px 12px', color: '#888', fontSize: 13 }}>
                  {p.last_scraped_at ? new Date(p.last_scraped_at).toLocaleString() : 'Never'}
                </td>
                <td style={{ padding: '10px 12px' }}>
                  <button onClick={() => { setEditing(p.id); setForm({ name: p.name, url: p.url, requires_auth: p.requires_auth, username: p.username || '', password: '', scrape_config: p.scrape_config || DEFAULT_CONFIG }); }} style={{ marginRight: 6 }}>Edit</button>
                  <button onClick={() => runOne(p.id)} disabled={status.is_running} style={{ marginRight: 6 }}>Run</button>
                  <button onClick={() => del(p.id)} style={{ color: '#ef4444' }}>Delete</button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {/* Add/Edit form */}
      <h3>{editing ? 'Edit Portal' : 'Add Portal'}</h3>
      {error && <div style={{ color: '#ef4444', marginBottom: 8 }}>{error}</div>}
      <div style={{ display: 'grid', gap: 10, maxWidth: 600 }}>
        <input placeholder="Name" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
        <input placeholder="URL" value={form.url} onChange={e => setForm(f => ({ ...f, url: e.target.value }))} />
        <label><input type="checkbox" checked={form.requires_auth} onChange={e => setForm(f => ({ ...f, requires_auth: e.target.checked }))} /> Requires Authentication</label>
        {form.requires_auth && <>
          <input placeholder="Username" value={form.username} onChange={e => setForm(f => ({ ...f, username: e.target.value }))} />
          <input type="password" placeholder="Password" value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))} />
        </>}
        <label style={{ color: '#888', fontSize: 13 }}>Scrape Config (JSON)</label>
        <textarea rows={10} value={form.scrape_config} onChange={e => setForm(f => ({ ...f, scrape_config: e.target.value }))} style={{ background: '#1e1e2e', border: '1px solid #333', color: '#e0e0e0', padding: 8, fontFamily: 'monospace', fontSize: 12 }} />
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={save}>{editing ? 'Update' : 'Add Portal'}</button>
          {editing && <button onClick={() => { setEditing(null); setForm({ name: '', url: '', requires_auth: false, username: '', password: '', scrape_config: DEFAULT_CONFIG }); }}>Cancel</button>}
        </div>
      </div>

      {/* Scrape logs */}
      <h3 style={{ marginTop: 32 }}>Scrape Logs</h3>
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
        </tbody>
      </table>
    </div>
  );
}
