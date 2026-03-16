import { useEffect, useState } from 'react';
import client from '../api/client';
import StatusBadge from './StatusBadge';

const STATUSES = ['new', 'under_review', 'approved', 'rejected'];

export default function TenderDetail({ tenderId, onClose }) {
  const [tender, setTender] = useState(null);
  const [notes, setNotes] = useState('');
  const [templates, setTemplates] = useState([]);
  const [selectedTemplate, setSelectedTemplate] = useState('');
  const [generating, setGenerating] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    client.get(`/tenders/${tenderId}`).then(r => {
      setTender(r.data);
      setNotes(r.data.notes || '');
    });
    client.get('/templates').then(r => {
      setTemplates(r.data.items);
      const def = r.data.items.find(t => t.is_default);
      if (def) setSelectedTemplate(String(def.id));
    });
  }, [tenderId]);

  const saveNotes = () => client.put(`/tenders/${tenderId}`, { notes }).then(r => setTender(r.data));
  const changeStatus = (status) => client.put(`/tenders/${tenderId}`, { status }).then(r => setTender(r.data));

  const generateProposal = async () => {
    if (!selectedTemplate) { setError('Select a template first'); return; }
    setGenerating(true);
    setError('');
    try {
      await client.post('/proposals', { tender_id: tenderId, template_id: Number(selectedTemplate) });
      alert('Proposal generated! Check the Proposals tab.');
    } catch (e) {
      setError(e.message);
    } finally {
      setGenerating(false);
    }
  };

  if (!tender) return null;

  return (
    <div style={{
      position: 'fixed', top: 0, right: 0, bottom: 0, width: 480,
      background: '#13131f', borderLeft: '1px solid #333',
      padding: 24, overflowY: 'auto', zIndex: 1000,
    }}>
      <button onClick={onClose} style={{ float: 'right', background: 'none', border: 'none', color: '#888', cursor: 'pointer', fontSize: 18 }}>✕</button>
      <h3 style={{ marginTop: 0 }}>{tender.title}</h3>

      <div style={{ marginBottom: 12 }}>
        <StatusBadge status={tender.status} />
        <select value={tender.status} onChange={e => changeStatus(e.target.value)} style={{ marginLeft: 8 }}>
          {STATUSES.map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
      </div>

      <table style={{ width: '100%', fontSize: 13, borderCollapse: 'collapse', marginBottom: 16 }}>
        {[
          ['Portal', tender.portal_name],
          ['Published', tender.published_date || '—'],
          ['Deadline', tender.deadline || '—'],
          ['Value', tender.estimated_value || '—'],
          ['Keywords', JSON.parse(tender.matched_keywords || '[]').join(', ')],
        ].map(([label, val]) => (
          <tr key={label}>
            <td style={{ color: '#888', padding: '4px 0', paddingRight: 12 }}>{label}</td>
            <td style={{ padding: '4px 0' }}>{val}</td>
          </tr>
        ))}
      </table>

      {tender.description && <p style={{ fontSize: 13, color: '#ccc', marginBottom: 16 }}>{tender.description}</p>}
      <a href={tender.source_url} target="_blank" rel="noreferrer" style={{ color: '#a89cf7', fontSize: 13 }}>View on portal ↗</a>

      <div style={{ marginTop: 20 }}>
        <label style={{ display: 'block', marginBottom: 4, color: '#888', fontSize: 13 }}>Notes</label>
        <textarea value={notes} onChange={e => setNotes(e.target.value)} rows={4} style={{ width: '100%', background: '#1e1e2e', border: '1px solid #333', borderRadius: 4, color: '#fff', padding: 8 }} />
        <button onClick={saveNotes} style={{ marginTop: 6 }}>Save Notes</button>
      </div>

      {tender.status === 'approved' && (
        <div style={{ marginTop: 20, padding: 16, background: '#1e2a1e', borderRadius: 8 }}>
          <h4 style={{ margin: '0 0 12px' }}>Generate Proposal</h4>
          <select value={selectedTemplate} onChange={e => setSelectedTemplate(e.target.value)} style={{ width: '100%', marginBottom: 8 }}>
            <option value="">Select template...</option>
            {templates.map(t => <option key={t.id} value={t.id}>{t.name} ({t.file_type.toUpperCase()})</option>)}
          </select>
          {error && <div style={{ color: '#ef4444', fontSize: 13, marginBottom: 8 }}>{error}</div>}
          <button onClick={generateProposal} disabled={generating} style={{ background: '#10b981', color: '#fff', border: 'none', borderRadius: 4, padding: '8px 16px', cursor: 'pointer' }}>
            {generating ? 'Generating...' : 'Generate Proposal'}
          </button>
        </div>
      )}
    </div>
  );
}
