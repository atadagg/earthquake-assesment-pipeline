export default function AddressFormatter({ value }) {
  if (!value || value === 'No address found.' || value === 'ADDRESS NOT DETECTED') return '—';
  
  try {
    const lines = value.split('\n').filter(Boolean);
    
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', width: '100%' }}>
        {lines.map((line, idx) => {
          const parts = line.split('|');
          let rawAddress = parts[0]?.trim();
          const latVal = parts[1]?.includes('LAT:') ? parts[1].replace('LAT:', '').trim() : null;
          const lngVal = parts[2]?.includes('LNG:') ? parts[2].replace('LNG:', '').trim() : null;
          const hasCoords = latVal && latVal !== 'N/A' && lngVal && lngVal !== 'N/A';

          if (!rawAddress) return null;

          // Clean up "Türkiye" at the end if present, for cleaner local view
          if (rawAddress.endsWith(', Türkiye')) {
            rawAddress = rawAddress.substring(0, rawAddress.length - 9);
          } else if (rawAddress.endsWith(', Turkey')) {
            rawAddress = rawAddress.substring(0, rawAddress.length - 8);
          }

          return (
            <div key={idx} style={{ 
              display: 'flex', 
              alignItems: 'center',
              justifyContent: 'space-between',
              gap: '8px',
              padding: '6px 10px', 
              borderRadius: '6px', 
              background: 'rgba(30, 41, 59, 0.4)',
              border: '1px solid rgba(255, 255, 255, 0.05)',
              width: '100%'
            }}>
              {/* Clean, unified address text */}
              <div style={{ 
                fontSize: '12px', 
                color: 'var(--text-primary)', 
                fontWeight: '500',
                lineHeight: '1.4',
                wordBreak: 'break-word',
                flex: 1
              }}>
                {rawAddress}
              </div>
              
              {/* Map Button (Only shown if coords exist, side-by-side on the same line) */}
              {hasCoords && (
                <a 
                  href={`https://www.google.com/maps/search/?api=1&query=${latVal},${lngVal}`} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  className="btn btn-ghost btn-sm"
                  style={{
                    padding: '2px 8px',
                    fontSize: '9.5px',
                    height: '20px',
                    lineHeight: '1',
                    borderRadius: '4px',
                    border: '1px solid var(--border-color)',
                    background: 'rgba(255,255,255,0.03)',
                    color: 'var(--accent-indigo)',
                    textDecoration: 'none',
                    fontWeight: '600',
                    flexShrink: 0
                  }}
                >
                  Harita
                </a>
              )}
            </div>
          );
        })}
      </div>
    );
  } catch (e) {
    return <div style={{ fontSize: '11px', wordBreak: 'break-word', color: 'var(--text-secondary)' }}>{String(value)}</div>;
  }
}
