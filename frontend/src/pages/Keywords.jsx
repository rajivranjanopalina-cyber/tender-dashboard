import { useEffect, useState } from 'react';
import client from '../api/client';

export default function KeywordsPage() {
  const [keywords, setKeywords] = useState([]);
  const [newKw, setNewKw] = useState('');
  const [error, setError] = useState('');

  const load = () => client.get('/keywords').then(r => setKeywords(r.data.items));
  useEffect(() => { load(); }, []);

  const add = async () => {
    if (!newKw.trim()) return;
    setError('');
    try {
      await client.post('/keywords', { value: newKw.trim(), active: true });
      setNewKw('');
      load();
    } catch (e) { setError(e.message); }
  };

  const toggle = async (kw) => {
    await client.put(`/keywords/${kw.id}`, { active: !kw.active });
    load();
  };

  const del = async (id) => {
    if (!confirm('Delete this keyword?')) return;
    await client.delete(`/keywords/${id}`);
    load();
  };

  return (
    <div>
      <h2>Keywords</h2>
      <p style={{ color: '#888', fontSize: 13 }}>Changes apply from the next scrape run.</p>

      <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
        <input
          placeholder="Add keyword..."
          value={newKw}
          onChange={e => setNewKw(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && add()}
        />
        <button onClick={add}>Add</button>
      </div>
      {error && <div style={{ color: '#ef4444', marginBottom: 8 }}>{error}</div>}

      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #333' }}>
            {['Keyword', 'Active', 'Actions'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: '#888' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {keywords.map(kw => (
            <tr key={kw.id} style={{ borderBottom: '1px solid #222' }}>
              <td style={{ padding: '10px 12px', fontFamily: 'monospace' }}>{kw.value}</td>
              <td style={{ padding: '10px 12px' }}>
                <input type="checkbox" checked={kw.active} onChange={() => toggle(kw)} />
              </td>
              <td style={{ padding: '10px 12px' }}>
                <button onClick={() => del(kw.id)} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
