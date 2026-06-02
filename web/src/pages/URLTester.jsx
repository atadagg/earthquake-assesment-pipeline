import { useState, useEffect } from 'react';
import { api } from '../api';
import StatCard from '../components/StatCard';
import DataTable from '../components/DataTable';
import LoadingSpinner from '../components/LoadingSpinner';
import AddressFormatter from '../components/AddressFormatter';
import ContentCell from '../components/ContentCell';

const NEED_MAP = {
  'K': 'Kurtarma',
  'G': 'Gıda/Su',
  'S': 'Sağlık',
  'B': 'Barınma',
  'I': 'Isıtma',
  'Y': 'Giyecek',
  'H': 'Hijyen',
  'U': 'Ulaşım',
  'M': 'Maddi Destek',
  'F': 'Yakıt',
  'N': '-',
};

export default function URLTester() {
  const [url, setUrl] = useState(() => sessionStorage.getItem('url_tester_url') || 'https://eksisozluk.com/6-subat-2023-kahramanmaras-depremi--7600868');
  const [maxEntries, setMaxEntries] = useState(() => Number(sessionStorage.getItem('url_tester_max')) || 200);
  const [classify, setClassify] = useState(() => {
    const val = sessionStorage.getItem('url_tester_classify');
    return val === null ? true : val === 'true';
  });
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState(() => {
    try {
      const saved = sessionStorage.getItem('url_tester_results');
      return saved ? JSON.parse(saved) : null;
    } catch (e) {
      return null;
    }
  });
  const [error, setError] = useState(null);
  const [activeFilter, setActiveFilter] = useState(() => sessionStorage.getItem('url_tester_filter') || 'all');

  useEffect(() => {
    sessionStorage.setItem('url_tester_url', url);
  }, [url]);

  useEffect(() => {
    sessionStorage.setItem('url_tester_max', maxEntries);
  }, [maxEntries]);

  useEffect(() => {
    sessionStorage.setItem('url_tester_classify', classify);
  }, [classify]);

  useEffect(() => {
    sessionStorage.setItem('url_tester_filter', activeFilter);
  }, [activeFilter]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!url.trim()) return;
    setLoading(true);
    setError(null);
    setResults(null);
    sessionStorage.removeItem('url_tester_results');
    setActiveFilter('all');
    try {
      const data = await api.scrapeClassify(url.trim(), maxEntries, classify);
      setResults(data);
      sessionStorage.setItem('url_tester_results', JSON.stringify(data));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const renderLabels = (_, row) => {
    const labels = row.labels || [];
    if (labels.length === 0) return <span className="label-badge other">—</span>;
    return (
      <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
        {labels.map((l) => (
          <span key={l} className={`label-badge ${l === 'H' ? 'damage' : l === 'Y' ? 'need' : l === 'B' ? 'info' : 'other'}`}>{l}</span>
        ))}
      </div>
    );
  };

  const columns = [
    { key: 'id', label: 'ID', width: '70px' },
    { key: 'author', label: 'Yazar', width: '110px' },
    { key: 'labels', label: 'Etiketler', width: '100px', render: renderLabels },
    { key: 'keywords', label: 'Anahtar Kelimeler', width: '220px', render: (_, row) => {
      const badges = [];
      if (row.is_damage && row.damage_keywords) {
        let dmg = [];
        try {
          dmg = typeof row.damage_keywords === 'string' ? JSON.parse(row.damage_keywords) : row.damage_keywords;
        } catch (e) {}
        if (Array.isArray(dmg)) {
          dmg.forEach(d => {
            const label = d === 'ÇH' ? 'Çok Hasarlı (ÇH)' : d === 'AH' ? 'Az Hasarlı (AH)' : d;
            badges.push(
              <span key={`dmg-${d}`} className="label-badge damage" style={{ fontSize: '11px', fontWeight: 600 }}>
                {label}
              </span>
            );
          });
        }
      }
      if (row.is_need && row.need_labels) {
        let needs = [];
        try {
          needs = typeof row.need_labels === 'string' ? JSON.parse(row.need_labels) : row.need_labels;
        } catch (e) {}
        if (Array.isArray(needs)) {
          needs.forEach(n => {
            if (n === 'N') {
              badges.push(<span key={`need-${n}`} style={{ color: 'var(--text-muted)', fontSize: '12px' }}>—</span>);
            } else {
              badges.push(
                <span key={`need-${n}`} className="label-badge need" style={{ fontSize: '11px', fontWeight: 600, background: 'rgba(245, 158, 11, 0.25)', border: '1px solid rgba(245, 158, 11, 0.4)' }}>
                  {NEED_MAP[n] || n}
                </span>
              );
            }
          });
        }
      }
      if (badges.length === 0) return '—';
      return (
        <div style={{ display: 'flex', gap: 4, flexWrap: 'wrap', alignItems: 'center' }}>
          {badges}
        </div>
      );
    }},
    { key: 'extracted_address', label: 'Adres', width: '310px', render: (v) => <AddressFormatter value={v} /> },
    { key: 'content', label: 'İçerik', className: 'content-cell', render: (v) => <ContentCell value={v} /> },
  ];

  const filteredEntries = results ? (results.entries || []).filter(entry => {
    if (activeFilter === 'all') return true;
    return (entry.labels || []).includes(activeFilter);
  }) : [];

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">URL Tester</h1>
        <p className="page-subtitle">Ekşi Sözlük URL'si girin — entry'leri çekip sınıflandıralım</p>
      </div>

      <div className="glass-card" style={{ marginBottom: 'var(--spacing-xl)' }}>
        <div className="glass-card-body">
          <form onSubmit={handleSubmit}>
            <div className="form-row" style={{ marginBottom: 'var(--spacing-md)' }}>
              <div style={{ flex: 3 }}>
                <label className="form-label">Ekşi Sözlük URL</label>
                <input type="url" className="form-input" placeholder="https://eksisozluk.com/..." value={url} onChange={(e) => setUrl(e.target.value)} required />
              </div>
              <div style={{ flex: 1, maxWidth: 120 }}>
                <label className="form-label">Maks Entry</label>
                <input type="number" className="form-input" value={maxEntries || ''} onChange={(e) => setMaxEntries(e.target.value === '' ? '' : parseInt(e.target.value, 10) || '')} onBlur={() => { if (!maxEntries || maxEntries < 10) setMaxEntries(10); }} min={10} max={2000} />
              </div>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <label className="checkbox-group">
                <input type="checkbox" checked={classify} onChange={(e) => setClassify(e.target.checked)} />
                Sınıflandır (H/Y/B + ihtiyaç + hasar + adres)
              </label>
              <button className="btn btn-primary" type="submit" disabled={loading} style={{ display: 'inline-flex', alignItems: 'center' }}>
                {loading ? (
                  <>
                    <span className="spinner sm" style={{ marginRight: 6 }} />
                    İşleniyor...
                  </>
                ) : (
                  <>
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}><polygon points="5 3 19 12 5 21 5 3"/></svg>
                    Çalıştır
                  </>
                )}
              </button>
            </div>
          </form>
        </div>
      </div>

      {error && (
        <div className="glass-card" style={{ marginBottom: 'var(--spacing-md)', borderColor: 'rgba(244,63,94,0.3)' }}>
          <div className="glass-card-body" style={{ color: 'var(--accent-rose)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>
            Hata: {error}
          </div>
        </div>
      )}

      {loading && <LoadingSpinner text="Entry'ler çekiliyor ve sınıflandırılıyor..." />}

      {results && !loading && (
        <>
          {results.stats && (
            <div className="stats-grid stagger" style={{ marginBottom: 'var(--spacing-xl)' }}>
              <StatCard 
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
                } 
                value={results.stats.total || 0} 
                label="Toplam" 
                variant="primary" 
              />
              <StatCard 
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
                } 
                value={results.stats.H || 0} 
                label="Hasar (H)" 
                variant="damage" 
              />
              <StatCard 
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
                } 
                value={results.stats.Y || 0} 
                label="Yardım (Y)" 
                variant="need" 
              />
              <StatCard 
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                } 
                value={results.stats.B || 0} 
                label="Bilgi (B)" 
                variant="info" 
              />
              <StatCard 
                icon={
                  <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M4 6h16M4 12h16M4 18h7"/></svg>
                } 
                value={results.stats.Other || 0} 
                label="Diğer" 
                variant="primary" 
              />
            </div>
          )}
          <div className="glass-card">
            <div className="glass-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
              <div className="glass-card-title" style={{ display: 'flex', alignItems: 'center' }}>
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></svg>
                Sonuçlar ({filteredEntries.length} entry)
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button className={`btn btn-sm ${activeFilter === 'all' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setActiveFilter('all')}>Tümü</button>
                <button className={`btn btn-sm ${activeFilter === 'H' ? 'btn-danger' : 'btn-ghost'}`} onClick={() => setActiveFilter('H')}>Hasar (H)</button>
                <button className={`btn btn-sm ${activeFilter === 'Y' ? '' : 'btn-ghost'}`} style={activeFilter === 'Y' ? { background: 'var(--gradient-need)', color: 'white' } : {}} onClick={() => setActiveFilter('Y')}>Yardım (Y)</button>
                <button className={`btn btn-sm ${activeFilter === 'B' ? '' : 'btn-ghost'}`} style={activeFilter === 'B' ? { background: 'var(--gradient-info)', color: 'white' } : {}} onClick={() => setActiveFilter('B')}>Bilgi (B)</button>
              </div>
            </div>
            <div className="glass-card-body" style={{ padding: 0 }}>
              <DataTable columns={columns} rows={filteredEntries} />
            </div>
          </div>
        </>
      )}
    </div>
  );
}
