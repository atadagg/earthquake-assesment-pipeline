import { useState } from 'react';
import { api } from '../api';
import LoadingSpinner from '../components/LoadingSpinner';

function MetricCard({ label, value, color }) {
  return (
    <div className="metric-card">
      <div className="metric-value" style={{ color }}>{value !== null ? `${(value * 100).toFixed(2)}%` : '—'}</div>
      <div className="metric-label">{label}</div>
    </div>
  );
}

function BenchmarkSection({ title, icon, metrics, color }) {
  return (
    <div className="glass-card" style={{ marginBottom: 'var(--spacing-md)' }}>
      <div className="glass-card-header">
        <div className="glass-card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ color, display: 'inline-flex', alignItems: 'center' }}>{icon}</span>
          {title}
        </div>
      </div>
      <div className="glass-card-body">
        <div className="metric-grid">
          <MetricCard label="Accuracy" value={metrics?.accuracy ?? null} color={color} />
          <MetricCard label="Precision" value={metrics?.precision ?? null} color={color} />
          <MetricCard label="Recall" value={metrics?.recall ?? null} color={color} />
          <MetricCard label="F1-Score" value={metrics?.f1 ?? null} color={color} />
        </div>
      </div>
    </div>
  );
}

export default function Validation() {
  const [generalResults, setGeneralResults] = useState(null);
  const [damageResults, setDamageResults] = useState(null);
  const [generalLoading, setGeneralLoading] = useState(false);
  const [damageLoading, setDamageLoading] = useState(false);
  const [generalSamples, setGeneralSamples] = useState(null);
  const [damageSamples, setDamageSamples] = useState(null);

  const runGeneral = async () => {
    setGeneralLoading(true);
    try {
      const data = await api.validate();
      setGeneralResults(data.results);
      setGeneralSamples(data.sample_count);
    } catch (err) {
      alert('Hata: ' + err.message);
    } finally {
      setGeneralLoading(false);
    }
  };

  const runDamage = async () => {
    setDamageLoading(true);
    try {
      const data = await api.validateDamage();
      setDamageResults(data.results);
      setDamageSamples(data.sample_count);
    } catch (err) {
      alert('Hata: ' + err.message);
    } finally {
      setDamageLoading(false);
    }
  };

  return (
    <div className="fade-in">
      <div className="page-header">
        <h1 className="page-title">Validation Benchmark</h1>
        <p className="page-subtitle">Sınıflandırıcıların doğruluğunu test veri seti üzerinde ölç</p>
      </div>

      <div style={{ display: 'flex', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-xl)' }}>
        <button className="btn btn-primary" onClick={runGeneral} disabled={generalLoading} style={{ display: 'inline-flex', alignItems: 'center' }}>
          {generalLoading ? (
            <>
              <span className="spinner sm" style={{ marginRight: 6 }} />
              Çalışıyor...
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
              Genel Pipeline Benchmark
            </>
          )}
        </button>
        <button className="btn btn-ghost" onClick={runDamage} disabled={damageLoading} style={{ display: 'inline-flex', alignItems: 'center' }}>
          {damageLoading ? (
            <>
              <span className="spinner sm" style={{ marginRight: 6 }} />
              Çalışıyor...
            </>
          ) : (
            <>
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/></svg>
              Hasar Lexicon Benchmark
            </>
          )}
        </button>
      </div>

      {(generalLoading || damageLoading) && (
        <LoadingSpinner text="Benchmark çalışıyor — bu işlem birkaç dakika sürebilir..." />
      )}

      {generalResults && (
        <>
          <p style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 'var(--spacing-md)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-emerald)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            Genel benchmark tamamlandı — {generalSamples} test örneği üzerinde
          </p>
          
          <BenchmarkSection 
            title="Hasar Modeli (H)" 
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            } 
            metrics={generalResults.H} 
            color="var(--accent-rose)" 
          />
          
          <BenchmarkSection 
            title="Yardım Modeli (Y)" 
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            } 
            metrics={generalResults.Y} 
            color="var(--accent-amber)" 
          />
          
          <BenchmarkSection 
            title="Bilgi Modeli (B)" 
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
            } 
            metrics={generalResults.B} 
            color="var(--accent-blue)" 
          />
        </>
      )}

      {damageResults && (
        <>
          <p style={{ color: 'var(--text-muted)', fontSize: 12, marginBottom: 'var(--spacing-md)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="var(--accent-emerald)" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
            Hasar lexicon benchmark tamamlandı — {damageSamples} test örneği üzerinde
          </p>
          
          <BenchmarkSection 
            title="Hasar Severity (DMG)" 
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>
            } 
            metrics={damageResults.DMG} 
            color="var(--accent-purple)" 
          />
        </>
      )}
    </div>
  );
}
