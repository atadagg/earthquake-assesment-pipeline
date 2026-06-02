import { useState } from 'react';
import { api } from '../api';

export default function DetectorTester() {
  const defaultTopics = `9 mart 2026 denizli depremi
galatasaray fenerbahçe derbisi
30 mart 2026 mersin depremi
iş başvurularında istenen absürt şartlar`;

  const [text, setText] = useState(defaultTopics);
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleTest = async () => {
    const titles = text.split('\n').map((t) => t.trim()).filter(Boolean);
    if (titles.length === 0) return;
    setLoading(true);
    try {
      const data = await api.detect(titles);
      setResults(data);
    } catch (err) {
      alert('Hata: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Detector Pattern Tester</h1>
        <p className="page-subtitle">Başlık girin — deprem pattern eşleşmesini test edin</p>
      </div>

      <div className="glass-card" style={{ marginBottom: 'var(--spacing-xl)' }}>
        <div className="glass-card-body">
          <label className="form-label">Başlıklar (her satır bir başlık)</label>
          <textarea className="form-input" rows={6} value={text} onChange={(e) => setText(e.target.value)} placeholder="Başlık yazın..." />
          <div style={{ marginTop: 'var(--spacing-md)', display: 'flex', justifyContent: 'flex-end' }}>
            <button className="btn btn-primary" onClick={handleTest} disabled={loading} style={{ display: 'inline-flex', alignItems: 'center' }}>
              {loading ? (
                <>
                  <span className="spinner sm" style={{ marginRight: 6 }} />
                  Test Ediliyor...
                </>
              ) : (
                <>
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                  Test Et
                </>
              )}
            </button>
          </div>
        </div>
      </div>

      {results && (
        <div className="glass-card">
          <div className="glass-card-header">
            <div className="glass-card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
              Sonuçlar
            </div>
            <span style={{ fontSize: 13, color: 'var(--text-muted)' }}>
              {results.matched}/{results.total} eşleşme
            </span>
          </div>
          <div className="glass-card-body" style={{ padding: 0 }}>
            <div className="data-table-wrapper">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Başlık</th>
                    <th style={{ width: 120 }}>Sonuç</th>
                    <th style={{ width: 300 }}>Ayrıntılar</th>
                  </tr>
                </thead>
                <tbody>
                  {results.results.map((r, i) => (
                    <tr key={i}>
                      <td>{r.title}</td>
                      <td>
                        <span 
                          className={`label-badge ${r.matched ? 'match' : 'no-match'}`}
                          style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}
                        >
                          {r.matched ? (
                            <>
                              <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                              EŞLEŞTİ
                            </>
                          ) : (
                            <>
                              <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg>
                              YOK
                            </>
                          )}
                        </span>
                      </td>
                      <td style={{ fontSize: 12, color: 'var(--text-muted)' }}>
                        {r.parsed ? (
                          <span>
                            {r.parsed.day} {r.parsed.month_name} {r.parsed.year} — <strong>{r.parsed.province}</strong>{' '}
                            ({r.parsed.confidence})
                          </span>
                        ) : '—'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
