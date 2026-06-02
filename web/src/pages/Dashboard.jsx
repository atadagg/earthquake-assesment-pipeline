import { useEffect, useState } from 'react';
import { api } from '../api';
import StatCard from '../components/StatCard';
import DataTable from '../components/DataTable';
import LogViewer from '../components/LogViewer';
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

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [entries, setEntries] = useState([]);
  const [pipelineStatus, setPipelineStatus] = useState({});
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [activeFilter, setActiveFilter] = useState('all');

  const loadData = async () => {
    try {
      const [s, e, ps] = await Promise.all([
        api.stats(),
        api.entries({ limit: 50 }),
        api.pipelineStatus(),
      ]);
      setStats(s);
      setEntries(e.entries || []);
      setPipelineStatus(ps);
    } catch (err) {
      console.error('Dashboard load error:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const id = setInterval(loadData, 10000);
    return () => clearInterval(id);
  }, []);

  const handleStartPipeline = async () => {
    setActionLoading(true);
    try {
      await api.startPipeline();
      setPipelineStatus((p) => ({ ...p, running: true }));
    } catch (err) {
      alert('Pipeline başlatılamadı: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const handleStopPipeline = async () => {
    setActionLoading(true);
    try {
      await api.stopPipeline();
      setPipelineStatus((p) => ({ ...p, running: false }));
    } catch (err) {
      alert('Pipeline durdurulamadı: ' + err.message);
    } finally {
      setActionLoading(false);
    }
  };

  const renderLabels = (_, row) => {
    const labels = [];
    if (row.is_damage) labels.push(<span key="H" className="label-badge damage">H</span>);
    if (row.is_need) labels.push(<span key="Y" className="label-badge need">Y</span>);
    if (row.is_info) labels.push(<span key="B" className="label-badge info">B</span>);
    if (labels.length === 0) labels.push(<span key="O" className="label-badge other">—</span>);
    return <div style={{ display: 'flex', gap: 4 }}>{labels}</div>;
  };

  const columns = [
    { key: 'entry_id', label: 'ID', width: '80px' },
    { key: 'author', label: 'Yazar', width: '110px' },
    { key: 'is_damage', label: 'Etiketler', width: '100px', render: renderLabels },
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

  const filteredEntries = (entries || []).filter(entry => {
    if (activeFilter === 'all') return true;
    if (activeFilter === 'H') return entry.is_damage;
    if (activeFilter === 'Y') return entry.is_need;
    if (activeFilter === 'B') return entry.is_info;
    return true;
  });

  if (loading) return <LoadingSpinner text="Dashboard yükleniyor..." />;

  return (
    <div className="fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle">Pipeline genel durumu ve son işlenen entry'ler</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {!pipelineStatus.running ? (
            <button className="btn btn-success" onClick={handleStartPipeline} disabled={actionLoading}>
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none" style={{ marginRight: 6 }}><polygon points="5 3 19 12 5 21 5 3"/></svg>
              Pipeline Başlat
            </button>
          ) : (
            <button className="btn btn-danger" onClick={handleStopPipeline} disabled={actionLoading}>
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor" stroke="none" style={{ marginRight: 6 }}><rect x="4" y="4" width="16" height="16" rx="2"/></svg>
              Pipeline Durdur
            </button>
          )}
          <button className="btn btn-ghost" onClick={loadData}>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38l5.67-5.67"/></svg>
            Yenile
          </button>
        </div>
      </div>

      {stats && (
        <div className="stats-grid stagger">
          <StatCard 
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/></svg>
            } 
            value={stats.total_entries} 
            label="Toplam Girdi" 
            variant="primary" 
          />
          <StatCard 
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="7.86 2 16.14 2 22 7.86 22 16.14 16.14 22 7.86 22 2 16.14 2 7.86 7.86 2"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
            } 
            value={stats.damage} 
            label="Hasar (H)" 
            variant="damage" 
          />
          <StatCard 
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>
            } 
            value={stats.need} 
            label="Yardım (Y)" 
            variant="need" 
          />
          <StatCard 
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
            } 
            value={stats.info} 
            label="Bilgi (B)" 
            variant="info" 
          />
          <StatCard 
            icon={
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></svg>
            } 
            value={stats.addresses_found} 
            label="Adres Bulunan" 
            variant="success" 
          />
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--spacing-md)', marginBottom: 'var(--spacing-xl)' }}>
        {/* Pipeline Control */}
        <div className="glass-card">
          <div className="glass-card-header">
            <div className="glass-card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <span className={`status-dot ${pipelineStatus.running ? 'active' : 'inactive'}`} style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%' }} />
              Pipeline Durumu
            </div>
            <span className={`label-badge ${pipelineStatus.running ? 'match' : 'other'}`}>
              {pipelineStatus.running ? 'Çalışıyor' : 'Durduruldu'}
            </span>
          </div>
          <div className="glass-card-body" style={{ padding: 0 }}>
            <LogViewer />
          </div>
        </div>

        {/* Quick Stats */}
        <div className="glass-card">
          <div className="glass-card-header">
            <div className="glass-card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>
              İstatistikler
            </div>
          </div>
          <div className="glass-card-body">
            <div style={{ display: 'grid', gap: 'var(--spacing-md)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Toplam Girdi</span>
                <span style={{ fontWeight: 700 }}>{stats?.total_entries?.toLocaleString('tr-TR') || 0}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)' }}>İşlenmiş Sonuç</span>
                <span style={{ fontWeight: 700 }}>{stats?.total_processed?.toLocaleString('tr-TR') || 0}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0', borderBottom: '1px solid var(--border-color)' }}>
                <span style={{ color: 'var(--text-muted)' }}>Etiketlenmemiş</span>
                <span style={{ fontWeight: 700 }}>{stats?.none?.toLocaleString('tr-TR') || 0}</span>
              </div>
              <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 0' }}>
                <span style={{ color: 'var(--text-muted)' }}>Classifier Durumu</span>
                <span className={`label-badge ${pipelineStatus.classifiers_loaded ? 'match' : 'no-match'}`}>
                  {pipelineStatus.classifiers_loaded ? 'Yüklendi' : pipelineStatus.classifiers_loading ? 'Yükleniyor...' : 'Bekleniyor'}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent entries table */}
      <div className="glass-card">
        <div className="glass-card-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 12 }}>
          <div className="glass-card-title" style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
            Son İşlenen Girdiler ({filteredEntries.length})
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            <button className={`btn btn-sm ${activeFilter === 'all' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setActiveFilter('all')}>Tümü</button>
            <button className={`btn btn-sm ${activeFilter === 'H' ? 'btn-danger' : 'btn-ghost'}`} onClick={() => setActiveFilter('H')}>Hasar (H)</button>
            <button className={`btn btn-sm ${activeFilter === 'Y' ? '' : 'btn-ghost'}`} style={activeFilter === 'Y' ? { background: 'var(--gradient-need)', color: 'white' } : {}} onClick={() => setActiveFilter('Y')}>Yardım (Y)</button>
            <button className={`btn btn-sm ${activeFilter === 'B' ? '' : 'btn-ghost'}`} style={activeFilter === 'B' ? { background: 'var(--gradient-info)', color: 'white' } : {}} onClick={() => setActiveFilter('B')}>Bilgi (B)</button>
          </div>
        </div>
        <div className="glass-card-body" style={{ padding: 0 }}>
          <DataTable columns={columns} rows={filteredEntries} emptyText="Filtreye uygun işlenmiş girdi bulunmamaktadır." />
        </div>
      </div>
    </div>
  );
}
