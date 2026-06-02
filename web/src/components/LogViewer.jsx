import { useEffect, useRef, useState } from 'react';
import { connectLogSocket } from '../api';

export default function LogViewer() {
  const [lines, setLines] = useState([]);
  const containerRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    wsRef.current = connectLogSocket((messages) => {
      setLines((prev) => {
        const next = [...prev, ...messages];
        // Keep last 500 lines
        return next.length > 500 ? next.slice(-500) : next;
      });
    });
    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, []);

  useEffect(() => {
    if (containerRef.current) {
      containerRef.current.scrollTop = containerRef.current.scrollHeight;
    }
  }, [lines]);

  return (
    <div className="log-viewer" ref={containerRef}>
      {lines.length === 0 ? (
        <div style={{ color: 'var(--text-muted)', fontStyle: 'italic' }}>
          Pipeline logları burada görünecek...
        </div>
      ) : (
        lines.map((line, i) => (
          <div key={i} className="log-line">
            {line}
          </div>
        ))
      )}
    </div>
  );
}
