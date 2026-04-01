import { useEffect, useState } from 'react';
import client from '../api/client';
import ConfirmDialog from '../components/ConfirmDialog';
import { useToast } from '../components/Toast';

export default function KeywordsPage() {
  const toast = useToast();
  const [keywords, setKeywords] = useState([]);
  const [newKw, setNewKw] = useState('');
  const [search, setSearch] = useState('');
  const [confirm, setConfirm] = useState(null);

  const load = () => client.get('/keywords').then(r => setKeywords(r.data.items)).catch(e => toast(e.message, 'error'));
  useEffect(() => { load(); }, []);

  const add = async () => {
    const values = newKw.split(',').map(v => v.trim()).filter(Boolean);
    if (values.length === 0) return;
    let added = 0;
    let errors = [];
    for (const value of values) {
      try {
        await client.post('/keywords', { value, active: true });
        added++;
      } catch (e) {
        errors.push(`"${value}": ${e.message}`);
      }
    }
    setNewKw('');
    load();
    if (added > 0) toast(`Added ${added} keyword${added > 1 ? 's' : ''}`, 'success');
    if (errors.length > 0) toast(errors[0], 'error');
  };

  const toggle = async (kw) => {
    try {
      await client.put(`/keywords/${kw.id}`, { active: !kw.active });
      load();
    } catch (e) { toast(e.message, 'error'); }
  };

  const del = (id, value) => {
    setConfirm({
      title: 'Delete Keyword',
      message: `Delete keyword "${value}"?`,
      onConfirm: async () => {
        setConfirm(null);
        try {
          await client.delete(`/keywords/${id}`);
          toast('Keyword deleted', 'success');
          load();
        } catch (e) { toast(e.message, 'error'); }
      },
    });
  };

  const filtered = keywords.filter(kw =>
    kw.value.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div>
      <h2>Keywords</h2>
      <p style={{ color: '#888', fontSize: 13 }}>Changes apply from the next scrape run.</p>

      {/* Add / Bulk add */}
      <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
        <input
          placeholder="Add keyword(s), comma-separated..."
          value={newKw}
          onChange={e => setNewKw(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
          style={{ flex: 1 }}
        />
        <button onClick={add}>Add</button>
      </div>
      <p style={{ color: '#555', fontSize: 12, marginBottom: 16 }}>Tip: enter comma-separated values to add multiple keywords at once.</p>

      {/* Search */}
      <div style={{ marginBottom: 16 }}>
        <input
          placeholder="Search keywords..."
          value={search}
          onChange={e => setSearch(e.target.value)}
          style={{ width: '100%', maxWidth: 320 }}
        />
      </div>

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #333' }}>
            {['Keyword', 'Active', 'Actions'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: '#888' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {filtered.map(kw => (
            <tr key={kw.id} style={{ borderBottom: '1px solid #222' }}>
              <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>{kw.value}</td>
              <td style={{ padding: '10px 12px' }}>
                <div
                  onClick={() => toggle(kw)}
                  title={kw.active ? 'Active — click to deactivate' : 'Inactive — click to activate'}
                  style={{
                    display: 'inline-flex', alignItems: 'center', gap: 6, cursor: 'pointer',
                  }}
                >
                  <div style={{
                    width: 10, height: 10, borderRadius: '50%',
                    background: kw.active ? '#10b981' : '#555',
                    flexShrink: 0,
                  }} />
                  <span style={{ color: kw.active ? '#10b981' : '#555', fontSize: 13 }}>
                    {kw.active ? 'Active' : 'Inactive'}
                  </span>
                </div>
              </td>
              <td style={{ padding: '10px 12px' }}>
                <button onClick={() => del(kw.id, kw.value)} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}>Delete</button>
              </td>
            </tr>
          ))}
          {filtered.length === 0 && (
            <tr><td colSpan={3} style={{ padding: '1rem', color: '#555', textAlign: 'center' }}>No keywords found.</td></tr>
          )}
        </tbody>
      </table>

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
