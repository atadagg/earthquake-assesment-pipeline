import { useState } from 'react';

export default function ContentCell({ value }) {
  const [expanded, setExpanded] = useState(false);
  const [hovered, setHovered] = useState(false);
  
  if (!value) return '—';

  return (
    <div 
      onClick={() => setExpanded(!expanded)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        cursor: 'pointer',
        whiteSpace: expanded ? 'normal' : 'nowrap',
        wordBreak: expanded ? 'break-word' : 'normal',
        maxWidth: expanded ? '600px' : '320px',
        overflow: 'hidden',
        textOverflow: 'ellipsis',
        background: expanded 
          ? 'rgba(255, 255, 255, 0.06)' 
          : (hovered ? 'rgba(255, 255, 255, 0.03)' : 'transparent'),
        padding: expanded ? '8px 12px' : '4px 6px',
        borderRadius: '4px',
        border: expanded ? '1px solid rgba(255, 255, 255, 0.08)' : '1px solid transparent',
        transition: 'all 0.15s ease',
        display: 'block',
        outline: 'none',
        userSelect: 'text',
        // Dotted underline indicator when collapsed & hovered to signal interactivity
        textDecoration: (!expanded && hovered) ? 'underline dotted rgba(255, 255, 255, 0.4)' : 'none',
      }}
      title={expanded ? "Daraltmak için tıklayın" : "Okumak ve genişletmek için tıklayın"}
    >
      {expanded ? value : value.replace(/\n/g, ' ')}
    </div>
  );
}
