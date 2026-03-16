import { useEffect, useRef, useState } from 'react';
import client from '../api/client';
import axios from 'axios';

const PLACEHOLDERS = [
  'tender_title', 'tender_description', 'tender_deadline',
  'tender_published_date', 'tender_estimated_value', 'tender_source_url',
  'tender_portal_name', 'tender_portal_url', 'generation_date',
];

export default function TemplatesPage() {
  const [templates, setTemplates] = useState([]);
  const [form, setForm] = useState({ name: '', description: '', is_default: false });
  const [file, setFile] = useState(null);
  const [error, setError] = useState('');
  const fileRef = useRef();

  const load = () => client.get('/templates').then(r => setTemplates(r.data.items));
  useEffect(() => { load(); }, []);

  const upload = async () => {
    if (!file || !form.name) { setError('Name and file are required'); return; }
    setError('');
    const fd = new FormData();
    fd.append('file', file);
    fd.append('name', form.name);
    if (form.description) fd.append('description', form.description);
    fd.append('is_default', form.is_default);
    try {
      await axios.post('/api/templates', fd, { headers: { 'Content-Type': 'multipart/form-data' } });
      setForm({ name: '', description: '', is_default: false });
      setFile(null);
      if (fileRef.current) fileRef.current.value = '';
      load();
    } catch (e) {
      setError(e.response?.data?.detail || e.message);
    }
  };

  const toggleDefault = async (t) => {
    await client.put(`/templates/${t.id}`, { is_default: !t.is_default });
    load();
  };

  const del = async (id) => {
    if (!confirm('Delete this template?')) return;
    try {
      await client.delete(`/templates/${id}`);
      load();
    } catch (e) { alert(e.message); }
  };

  return (
    <div>
      <h2>Templates</h2>

      {/* Upload form */}
      <div style={{ background: '#1e1e2e', borderRadius: 8, padding: 20, marginBottom: 24, maxWidth: 500 }}>
        <h3 style={{ margin: '0 0 16px' }}>Upload Template</h3>
        {error && <div style={{ color: '#ef4444', marginBottom: 8 }}>{error}</div>}
        <div style={{ display: 'grid', gap: 10 }}>
          <input placeholder="Template name *" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
          <input placeholder="Description (optional)" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          <input ref={fileRef} type="file" accept=".pdf,.docx" onChange={e => setFile(e.target.files[0])} />
          <label><input type="checkbox" checked={form.is_default} onChange={e => setForm(f => ({ ...f, is_default: e.target.checked }))} /> Set as default template</label>
          <button onClick={upload}>Upload</button>
        </div>
      </div>

      {/* Placeholder reference */}
      <details style={{ marginBottom: 24, background: '#1e1e2e', borderRadius: 8, padding: 16 }}>
        <summary style={{ cursor: 'pointer', color: '#a89cf7' }}>Placeholder Reference</summary>
        <p style={{ color: '#888', fontSize: 13, margin: '8px 0' }}>Use these in DOCX as <code style={{ color: '#ffe082' }}>{'{{placeholder}}'}</code> or as PDF AcroForm field names.</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
          {PLACEHOLDERS.map(p => (
            <code key={p} style={{ background: '#13131f', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>{`{{${p}}}`}</code>
          ))}
        </div>
      </details>

      {/* Template table */}
      <table style={{ width: '100%', borderCollapse: 'collapse' }}>
        <thead>
          <tr style={{ borderBottom: '1px solid #333' }}>
            {['Name', 'Type', 'Default', 'Uploaded', 'Actions'].map(h => (
              <th key={h} style={{ textAlign: 'left', padding: '8px 12px', color: '#888' }}>{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {templates.map(t => (
            <tr key={t.id} style={{ borderBottom: '1px solid #222' }}>
              <td style={{ padding: '10px 12px' }}>{t.name}</td>
              <td style={{ padding: '10px 12px' }}><span style={{ fontFamily: 'monospace', fontSize: 12 }}>{t.file_type.toUpperCase()}</span></td>
              <td style={{ padding: '10px 12px' }}>
                <input type="checkbox" checked={t.is_default} onChange={() => toggleDefault(t)} />
              </td>
              <td style={{ padding: '10px 12px', color: '#888', fontSize: 13 }}>{new Date(t.created_at).toLocaleDateString()}</td>
              <td style={{ padding: '10px 12px' }}>
                <a href={`/api/templates/${t.id}/download`} target="_blank" rel="noreferrer" style={{ color: '#a89cf7', marginRight: 8, fontSize: 13 }}>Download</a>
                <button onClick={() => del(t.id)} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}>Delete</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
