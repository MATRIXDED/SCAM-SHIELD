import React from 'react';

export default function Sidebar({ activeTab, setActiveTab, backendStatus }) {
  const navItems = [
    { id: 'scan', label: 'Scan Message', icon: 'security' },
    { id: 'history', label: 'Recent Checks', icon: 'history' },
    { id: 'family', label: 'Family Safety', icon: 'family_restroom' },
    { id: 'guide', label: 'Safety Guide', icon: 'verified_user' },
    { id: 'settings', label: 'System Diagnostics', icon: 'settings' },
  ];

  return (
    <aside className="app-sidebar" aria-label="Main Navigation">
      <div>
        {/* Brand Header */}
        <div className="brand-header">
          <div className="brand-icon-shield" aria-hidden="true">
            <span className="material-symbols-outlined text-[24px]">shield</span>
          </div>
          <div className="brand-text">
            <h1>ScamShield</h1>
            <div className="brand-tagline">Pause the pressure. Check the message.</div>
          </div>
        </div>

        <div className="sidebar-divider" />

        {/* Navigation list */}
        <nav className="sidebar-nav" role="tablist">
          {navItems.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              aria-selected={activeTab === item.id}
              className={`nav-item-btn ${activeTab === item.id ? 'active' : ''}`}
              onClick={() => setActiveTab(item.id)}
            >
              <span className="material-symbols-outlined text-[20px]">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </nav>
      </div>

      {/* Bottom Privacy & Telemetry Card */}
      <div className="sidebar-privacy-card">
        <div className="privacy-card-title">
          <span className="material-symbols-outlined text-[16px]">lock</span>
          <span>Zero Raw Message Storage</span>
        </div>
        <p className="privacy-card-desc">
          Evaluated in memory. Raw message bodies are never written to disk or database tables.
        </p>
        <div className="privacy-card-footer">
          <span style={{ color: 'var(--teal-secondary)', fontWeight: 600 }}>
            {backendStatus.mode === 'supabase_cloud' ? '● Supabase Cloud' : '● Local SQLite Demo'}
          </span>
          <span style={{ opacity: 0.7 }}>Hackathon Track</span>
        </div>
      </div>
    </aside>
  );
}
