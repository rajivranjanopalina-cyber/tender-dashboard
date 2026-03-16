import { useState } from 'react';
import Dashboard from './pages/Dashboard';
import ScraperPage from './pages/Scraper';
import KeywordsPage from './pages/Keywords';
import TemplatesPage from './pages/Templates';
import ProposalsPage from './pages/Proposals';

const TABS = [
  { id: 'dashboard', label: 'Dashboard' },
  { id: 'scraper', label: 'Scraper' },
  { id: 'keywords', label: 'Keywords' },
  { id: 'templates', label: 'Templates' },
  { id: 'proposals', label: 'Proposals' },
];

const PAGE_MAP = {
  dashboard: Dashboard,
  scraper: ScraperPage,
  keywords: KeywordsPage,
  templates: TemplatesPage,
  proposals: ProposalsPage,
};

export default function App() {
  const [tab, setTab] = useState('dashboard');
  const Page = PAGE_MAP[tab];

  return (
    <div style={{ fontFamily: 'system-ui, sans-serif', background: '#0d0d1a', color: '#e0e0e0', minHeight: '100vh' }}>
      <nav style={{ background: '#13131f', borderBottom: '1px solid #222', padding: '0 24px', display: 'flex', alignItems: 'center', gap: 4 }}>
        <span style={{ fontWeight: 700, color: '#a89cf7', marginRight: 24, padding: '16px 0' }}>TenderHub</span>
        {TABS.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            style={{
              background: 'none', border: 'none', cursor: 'pointer',
              color: tab === t.id ? '#a89cf7' : '#888',
              borderBottom: tab === t.id ? '2px solid #a89cf7' : '2px solid transparent',
              padding: '16px 12px', fontWeight: tab === t.id ? 600 : 400,
            }}
          >
            {t.label}
          </button>
        ))}
      </nav>
      <main style={{ padding: 24, maxWidth: 1200, margin: '0 auto' }}>
        <Page />
      </main>
    </div>
  );
}
