import { useState } from 'react';
import client from '../api/client';

export default function Login({ onLogin }) {
  const [password, setPassword] = useState('');
  const [rememberMe, setRememberMe] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await client.post('/auth', { password, remember_me: rememberMe });
      localStorage.setItem('token', res.data.token);
      onLogin();
    } catch (err) {
      setError(err.message || 'Invalid password');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{
      minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center',
      background: '#0d0d1a', color: '#e0e0e0', fontFamily: 'Inter, system-ui, sans-serif',
    }}>
      <form onSubmit={handleSubmit} style={{
        background: '#1a1a2e', padding: '2.5rem', borderRadius: '12px',
        width: '100%', maxWidth: '400px', boxShadow: '0 4px 24px rgba(0,0,0,0.3)',
      }}>
        <h1 style={{ textAlign: 'center', marginBottom: '0.5rem', color: '#a89cf7' }}>
          Tender Dashboard
        </h1>
        <p style={{ textAlign: 'center', marginBottom: '2rem', color: '#888', fontSize: '0.9rem' }}>
          Enter password to continue
        </p>

        {error && (
          <div style={{
            background: '#ff4d4f22', border: '1px solid #ff4d4f', borderRadius: '6px',
            padding: '0.75rem', marginBottom: '1rem', color: '#ff4d4f', fontSize: '0.85rem',
          }}>
            {error}
          </div>
        )}

        <input
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Password"
          autoFocus
          style={{
            width: '100%', padding: '0.75rem', borderRadius: '6px', border: '1px solid #333',
            background: '#0d0d1a', color: '#e0e0e0', fontSize: '1rem', marginBottom: '1rem',
            boxSizing: 'border-box',
          }}
        />

        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1.5rem', cursor: 'pointer' }}>
          <input
            type="checkbox"
            checked={rememberMe}
            onChange={(e) => setRememberMe(e.target.checked)}
          />
          <span style={{ fontSize: '0.85rem', color: '#888' }}>Remember me (7 days)</span>
        </label>

        <button
          type="submit"
          disabled={loading || !password}
          style={{
            width: '100%', padding: '0.75rem', borderRadius: '6px', border: 'none',
            background: '#a89cf7', color: '#0d0d1a', fontSize: '1rem', fontWeight: '600',
            cursor: loading ? 'wait' : 'pointer', opacity: loading || !password ? 0.6 : 1,
          }}
        >
          {loading ? 'Signing in...' : 'Sign In'}
        </button>
      </form>
    </div>
  );
}
