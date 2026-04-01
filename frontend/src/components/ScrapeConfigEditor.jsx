import { useState, useEffect } from 'react';

const FIELD_LABELS = [
  { key: 'list_selector', label: 'Tender List Container', placeholder: 'e.g., table.tenders tbody tr' },
  { key: 'fields.title', label: 'Title Selector', placeholder: 'e.g., td.title' },
  { key: 'fields.description', label: 'Description Selector', placeholder: 'e.g., td.description' },
  { key: 'fields.deadline', label: 'Deadline Selector', placeholder: 'e.g., td.deadline' },
  { key: 'fields.estimated_value', label: 'Estimated Value Selector', placeholder: 'e.g., td.value' },
  { key: 'fields.source_url', label: 'Source URL Selector', placeholder: 'e.g., td a@href' },
  { key: 'next_button', label: 'Next Page Button', placeholder: 'e.g., a.next-page' },
  { key: 'date_format', label: 'Date Format', placeholder: 'e.g., %d/%m/%Y' },
  { key: 'renderer', label: 'Renderer', placeholder: 'default or external' },
];

const inputStyle = {
  width: '100%', padding: '0.5rem', borderRadius: '4px', border: '1px solid #333',
  background: '#0d0d1a', color: '#e0e0e0', fontSize: '0.85rem', boxSizing: 'border-box',
};

export default function ScrapeConfigEditor({ value, onChange }) {
  const [mode, setMode] = useState('form');
  const [jsonText, setJsonText] = useState(value || '{}');
  const [jsonError, setJsonError] = useState('');

  const config = (() => {
    try { return JSON.parse(value || '{}'); } catch { return {}; }
  })();

  const updateField = (dotPath, val) => {
    const newConfig = { ...config };
    const parts = dotPath.split('.');
    if (parts.length === 2) {
      if (!newConfig[parts[0]]) newConfig[parts[0]] = {};
      newConfig[parts[0]][parts[1]] = val;
    } else {
      newConfig[parts[0]] = val;
    }
    const json = JSON.stringify(newConfig, null, 2);
    setJsonText(json);
    onChange(json);
  };

  const getField = (dotPath) => {
    const parts = dotPath.split('.');
    if (parts.length === 2) return config[parts[0]]?.[parts[1]] || '';
    return config[parts[0]] || '';
  };

  const handleJsonChange = (text) => {
    setJsonText(text);
    try {
      JSON.parse(text);
      setJsonError('');
      onChange(text);
    } catch (e) {
      setJsonError(e.message);
    }
  };

  useEffect(() => {
    setJsonText(value || '{}');
  }, [value]);

  return (
    <div>
      <div style={{ display: 'flex', gap: '0.5rem', marginBottom: '1rem' }}>
        <button
          type="button"
          onClick={() => setMode('form')}
          style={{
            padding: '0.4rem 1rem', borderRadius: '4px', border: '1px solid #333',
            background: mode === 'form' ? '#a89cf7' : 'transparent',
            color: mode === 'form' ? '#0d0d1a' : '#e0e0e0', cursor: 'pointer', fontWeight: 600,
          }}
        >Form</button>
        <button
          type="button"
          onClick={() => setMode('json')}
          style={{
            padding: '0.4rem 1rem', borderRadius: '4px', border: '1px solid #333',
            background: mode === 'json' ? '#a89cf7' : 'transparent',
            color: mode === 'json' ? '#0d0d1a' : '#e0e0e0', cursor: 'pointer', fontWeight: 600,
          }}
        >JSON</button>
      </div>

      {mode === 'form' ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          {FIELD_LABELS.map(({ key, label, placeholder }) => (
            <div key={key}>
              <label style={{ fontSize: '0.8rem', color: '#888', marginBottom: '0.25rem', display: 'block' }}>
                {label}
              </label>
              <input
                style={inputStyle}
                value={getField(key)}
                onChange={(e) => updateField(key, e.target.value)}
                placeholder={placeholder}
              />
            </div>
          ))}
        </div>
      ) : (
        <div>
          <textarea
            value={jsonText}
            onChange={(e) => handleJsonChange(e.target.value)}
            style={{
              ...inputStyle, minHeight: '250px', fontFamily: 'monospace', resize: 'vertical',
            }}
          />
          {jsonError && <div style={{ color: '#ff4d4f', fontSize: '0.8rem', marginTop: '0.25rem' }}>{jsonError}</div>}
        </div>
      )}
    </div>
  );
}
