import { useEffect, useState, useCallback } from 'react';
import { api } from '../api';
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

export default function DBBrowser() {
  const [entries, setEntries] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [filterOptions, setFilterOptions] = useState({ earthquake_ids: [], thread_paths: [] });
  const [clearingDb, setClearingDb] = useState(false);

  // Filters
  const [filters, setFilters] = useState({
    earthquake_id: '',
    thread_path: '',
    label: '',
    keyword: '',
    need_label: '',
    content: '',
    only_address: false,
    limit: 100,
    offset: 0,
  });

  const loadEntries = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api.entries(filters);
      setEntries(data.entries || []);
      setTotal(data.total || 0);
    } catch (err) {
      console.error('DB Browser error:', err);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadEntries();
  }, [loadEntries]);

  useEffect(() => {
    api.filters().then(setFilterOptions).catch(() => {});
  }, []);

  const updateFilter = (key, value) => {
    setFilters((prev) => ({ ...prev, [key]: value, offset: 0 }));
  };

  const handleExport = () => {
    window.open(api.exportUrl(), '_blank');
  };

  const handleClearDb = async () => {
    if (!window.confirm('Tüm entry ve sonuçları kalıcı olarak silmek istediğinize emin misiniz?')) return;
    setClearingDb(true);
    try {
      await api.clearDb();
      await loadEntries();
      alert('Veritabanı temizlendi.');
    } catch (err) {
      alert('Hata: ' + err.message);
    } finally {
      setClearingDb(false);
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
    { key: 'entry_id', label: 'ID', width: '70px' },
    { key: 'earthquake_id', label: 'Deprem ID', width: '130px' },
    { key: 'author', label: 'Yazar', width: '100px' },
    { key: 'timestamp', label: 'Tarih', width: '120px' },
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

  const page = Math.floor(filters.offset / filters.limit) + 1;
  const totalPages = Math.ceil(total / filters.limit);

  return (
    <div className="fade-in">
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <h1 className="page-title">DB Browser</h1>
          <p className="page-subtitle">Pipeline veritabanındaki entry ve sonuçları filtrele ve incele</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button className="btn btn-ghost" onClick={handleExport}>
            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
            Excel Dışa Aktar
          </button>
          <button className="btn btn-danger btn-sm" onClick={handleClearDb} disabled={clearingDb}>
            <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ marginRight: 6 }}><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"/></svg>
            DB Temizle
          </button>
        </div>
      </div>

      {/* Filters */}
      <div className="glass-card" style={{ marginBottom: 'var(--spacing-md)' }}>
        <div className="filters-bar">
          <select
            className="form-input"
            value={filters.earthquake_id}
            onChange={(e) => updateFilter('earthquake_id', e.target.value)}
          >
            <option value="">Tüm Depremler</option>
            {filterOptions.earthquake_ids.map((id) => (
              <option key={id} value={id}>{id}</option>
            ))}
          </select>

          <select
            className="form-input"
            value={filters.thread_path}
            onChange={(e) => updateFilter('thread_path', e.target.value)}
          >
            <option value="">Tüm Thread'ler</option>
            {filterOptions.thread_paths.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>

          <select
            className="form-input"
            value={filters.label}
            onChange={(e) => updateFilter('label', e.target.value)}
          >
            <option value="">Tüm Etiketler</option>
            <option value="H">Hasar (H)</option>
            <option value="Y">Yardım (Y)</option>
            <option value="B">Bilgi (B)</option>
          </select>

          <input
            type="text"
            className="form-input"
            placeholder="Hasar keyword ara..."
            value={filters.keyword}
            onChange={(e) => updateFilter('keyword', e.target.value)}
          />

          <input
            type="text"
            className="form-input"
            placeholder="İçerikte ara..."
            value={filters.content}
            onChange={(e) => updateFilter('content', e.target.value)}
          />

          <label className="checkbox-group" style={{ maxWidth: 160 }}>
            <input
              type="checkbox"
              checked={filters.only_address}
              onChange={(e) => updateFilter('only_address', e.target.checked)}
            />
            Sadece adresli
          </label>
        </div>
      </div>

      {/* Results */}
      <div className="glass-card">
        <div className="glass-card-header">
          <div className="glass-card-title" style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/></svg>
            Kayıtlar
            <span style={{ color: 'var(--text-muted)', fontWeight: 400, fontSize: 12, marginLeft: 8 }}>
              ({total.toLocaleString('tr-TR')} kayıt)
            </span>
          </div>
          <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
            <button
              className="btn btn-ghost btn-sm"
              style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: 6 }}
              disabled={page <= 1}
              onClick={() => setFilters((p) => ({ ...p, offset: p.offset - p.limit }))}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="15 18 9 12 15 6"/></svg>
            </button>
            <span style={{ fontSize: 12, color: 'var(--text-muted)' }}>
              {page} / {totalPages || 1}
            </span>
            <button
              className="btn btn-ghost btn-sm"
              style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: 6 }}
              disabled={page >= totalPages}
              onClick={() => setFilters((p) => ({ ...p, offset: p.offset + p.limit }))}
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="9 18 15 12 9 6"/></svg>
            </button>
          </div>
        </div>
        <div className="glass-card-body" style={{ padding: 0 }}>
          {loading ? <LoadingSpinner /> : <DataTable columns={columns} rows={entries} />}
        </div>
      </div>
    </div>
  );
}
