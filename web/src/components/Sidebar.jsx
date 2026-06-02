import { NavLink, useLocation } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { api } from '../api';

const navItems = [
  { 
    path: '/', 
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <rect x="3" y="3" width="7" height="9"/>
        <rect x="14" y="3" width="7" height="5"/>
        <rect x="14" y="12" width="7" height="9"/>
        <rect x="3" y="16" width="7" height="5"/>
      </svg>
    ), 
    label: 'Dashboard', 
    section: 'Genel' 
  },
  { 
    path: '/db-browser', 
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <ellipse cx="12" cy="5" rx="9" ry="3"/>
        <path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/>
        <path d="M3 12c0 1.66 4 3 9 3s9-1.34 9-3"/>
      </svg>
    ), 
    label: 'DB Browser', 
    section: 'Genel' 
  },
  { 
    path: '/url-tester', 
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
        <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
      </svg>
    ), 
    label: 'URL Tester', 
    section: 'Test' 
  },
  { 
    path: '/detector', 
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
      </svg>
    ), 
    label: 'Detector Tester', 
    section: 'Test' 
  },
  { 
    path: '/validation', 
    icon: (
      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
        <line x1="18" y1="20" x2="18" y2="10"/>
        <line x1="12" y1="20" x2="12" y2="4"/>
        <line x1="6" y1="20" x2="6" y2="14"/>
      </svg>
    ), 
    label: 'Benchmark', 
    section: 'Test' 
  },
];

export default function Sidebar() {
  const [status, setStatus] = useState({ running: false, classifiers_loaded: false, classifiers_loading: false });

  useEffect(() => {
    const poll = () => api.pipelineStatus().then(setStatus).catch(() => {});
    poll();
    const id = setInterval(poll, 5000);
    return () => clearInterval(id);
  }, []);

  let sections = {};
  navItems.forEach((item) => {
    if (!sections[item.section]) sections[item.section] = [];
    sections[item.section].push(item);
  });

  const statusLabel = status.running
    ? 'Pipeline Aktif'
    : status.classifiers_loading
    ? 'Classifier Yükleniyor...'
    : status.classifiers_loaded
    ? 'Hazır — Pipeline Durdu'
    : 'Başlatılıyor...';

  const dotClass = status.running ? 'active' : status.classifiers_loading ? 'loading' : 'inactive';

  return (
    <aside className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo" style={{ background: 'var(--gradient-primary)', color: 'white' }}>
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <circle cx="12" cy="12" r="10"/>
            <line x1="2" y1="12" x2="22" y2="12"/>
            <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
          </svg>
        </div>
        <div className="sidebar-brand">
          Deprem Pipeline
          <small>Earthquake Assessment</small>
        </div>
      </div>

      <nav className="sidebar-nav">
        {Object.entries(sections).map(([section, items]) => (
          <div key={section}>
            <div className="nav-label">{section}</div>
            {items.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}
              >
                <span className="nav-icon" style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
                  {item.icon}
                </span>
                <span>{item.label}</span>
              </NavLink>
            ))}
          </div>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="pipeline-status">
          <span className={`status-dot ${dotClass}`} />
          <span>{statusLabel}</span>
        </div>
      </div>
    </aside>
  );
}
