import { useEffect, useRef, useState } from 'react';
import client from '../api/client';
import ConfirmDialog from '../components/ConfirmDialog';
import { useToast } from '../components/Toast';

const PLACEHOLDERS = [
  '{{tender_title}}', '{{tender_description}}', '{{tender_deadline}}',
  '{{tender_published_date}}', '{{tender_estimated_value}}', '{{tender_source_url}}',
  '{{tender_portal_name}}', '{{tender_portal_url}}', '{{generation_date}}',
  '{{company_name}}', '{{company_address}}', '{{company_contact}}',
];

export default function TemplatesPage() {
  const toast = useToast();
  const [templates, setTemplates] = useState([]);
  const [form, setForm] = useState({ name: '', description: '', is_default: false });
  const [file, setFile] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [dragOver, setDragOver] = useState(false);
  const [confirm, setConfirm] = useState(null);
  const fileRef = useRef();

  const load = () => client.get('/templates').then(r => setTemplates(r.data.items)).catch(e => toast(e.message, 'error'));
  useEffect(() => { load(); }, []);

  const handleFile = (f) => {
    if (!f) return;
    const ext = f.name.split('.').pop().toLowerCase();
    if (!['docx'].includes(ext)) {
      toast('Only .docx files are supported', 'error');
      return;
    }
    if (f.size > 10 * 1024 * 1024) {
      toast('File must be under 10 MB', 'error');
      return;
    }
    setFile(f);
  };

  const upload = async () => {
    if (!file || !form.name) { toast('Name and file are required', 'error'); return; }
    setUploading(true);
    const token = localStorage.getItem('token');
    const fd = new FormData();
    fd.append('file', file);
    fd.append('name', form.name);
    if (form.description) fd.append('description', form.description);
    fd.append('is_default', form.is_default);
    try {
      await fetch('/api/templates', {
        method: 'POST',
        headers: token ? { Authorization: `Bearer ${token}` } : {},
        body: fd,
      }).then(async (r) => {
        if (!r.ok) {
          const data = await r.json().catch(() => ({}));
          throw new Error(data.detail || 'Upload failed');
        }
        return r.json();
      });
      setForm({ name: '', description: '', is_default: false });
      setFile(null);
      if (fileRef.current) fileRef.current.value = '';
      toast('Template uploaded', 'success');
      load();
    } catch (e) {
      toast(e.message, 'error');
    } finally {
      setUploading(false);
    }
  };

  const toggleDefault = async (t) => {
    try {
      await client.put(`/templates/${t.id}`, { is_default: !t.is_default });
      load();
    } catch (e) { toast(e.message, 'error'); }
  };

  const del = (id, name) => {
    setConfirm({
      title: 'Delete Template',
      message: `Delete template "${name}"?`,
      onConfirm: async () => {
        setConfirm(null);
        try {
          await client.delete(`/templates/${id}`);
          toast('Template deleted', 'success');
          load();
        } catch (e) { toast(e.message, 'error'); }
      },
    });
  };

  return (
    <div>
      <h2>Templates</h2>

      {/* Upload form */}
      <div style={{ background: '#1e1e2e', borderRadius: 8, padding: 20, marginBottom: 24, maxWidth: 500 }}>
        <h3 style={{ margin: '0 0 16px' }}>Upload Template</h3>

        {/* Drop zone */}
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => { e.preventDefault(); setDragOver(false); handleFile(e.dataTransfer.files[0]); }}
          onClick={() => fileRef.current?.click()}
          style={{
            border: `2px dashed ${dragOver ? '#a89cf7' : '#333'}`,
            borderRadius: 8, padding: '1.5rem', textAlign: 'center', cursor: 'pointer',
            marginBottom: 12, background: dragOver ? '#a89cf711' : 'transparent',
            transition: 'all 0.15s',
          }}
        >
          {file
            ? <span style={{ color: '#10b981' }}>{file.name} ({(file.size / 1024).toFixed(0)} KB)</span>
            : <span style={{ color: '#888' }}>Drop .docx here or click to browse</span>
          }
          <input ref={fileRef} type="file" accept=".docx" style={{ display: 'none' }} onChange={e => handleFile(e.target.files[0])} />
        </div>

        <div style={{ display: 'grid', gap: 10 }}>
          <input placeholder="Template name *" value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} />
          <input placeholder="Description (optional)" value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
          <label><input type="checkbox" checked={form.is_default} onChange={e => setForm(f => ({ ...f, is_default: e.target.checked }))} /> Set as default template</label>
          <button onClick={upload} disabled={uploading}>{uploading ? 'Uploading...' : 'Upload'}</button>
        </div>
      </div>

      {/* Placeholder reference */}
      <details style={{ marginBottom: 24, background: '#1e1e2e', borderRadius: 8, padding: 16 }}>
        <summary style={{ cursor: 'pointer', color: '#a89cf7' }}>Placeholder Reference</summary>
        <p style={{ color: '#888', fontSize: 13, margin: '8px 0' }}>
          Use these in your DOCX template as <code style={{ color: '#ffe082' }}>{'{{placeholder}}'}</code>
        </p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 8 }}>
          {PLACEHOLDERS.map(p => (
            <code key={p} style={{ background: '#13131f', padding: '2px 8px', borderRadius: 4, fontSize: 12 }}>{p}</code>
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
                {t.blob_url
                  ? <a href={t.blob_url} target="_blank" rel="noreferrer" style={{ color: '#a89cf7', marginRight: 8, fontSize: 13 }}>Download</a>
                  : <a href={`/api/templates/${t.id}/download`} target="_blank" rel="noreferrer" style={{ color: '#a89cf7', marginRight: 8, fontSize: 13 }}>Download</a>
                }
                <button onClick={() => del(t.id, t.name)} style={{ color: '#ef4444', background: 'none', border: 'none', cursor: 'pointer' }}>Delete</button>
              </td>
            </tr>
          ))}
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
