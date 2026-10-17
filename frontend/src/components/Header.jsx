import React from 'react';

export default function Header({ activeTab, backendStatus }) {
  const tabTitles = {
    scan: 'Message Inspection',
    history: 'Recent Checks',
    family: 'Family Safety',
    guide: 'Safety Guide',
    settings: 'System Diagnostics',
  };

  return (
    <header className="app-header" role="banner">
      <div className="header-left">
        <div className="header-breadcrumb">
          <span className="breadcrumb-root">ScamShield</span>
          <span className="material-symbols-outlined text-[16px]">chevron_right</span>
          <span>{tabTitles[activeTab] || 'Console'}</span>
        </div>
        <span className="prototype-pill">
          <span className="material-symbols-outlined text-[14px]">info</span>
          Prototype Track
        </span>
      </div>

      <div className="header-right">
        <div className={`status-badge-live ${backendStatus.supabase_configured ? '' : 'demo'}`}>
          <span className="live-dot" />
          <span>{backendStatus.supabase_configured ? 'Supabase Cloud' : 'Local SQLite Demo'}</span>
        </div>

        <a
          href="tel:18773824357"
          className="helpline-link"
          title="Direct consumer hotline for FTC fraud reporting"
        >
          <span className="material-symbols-outlined text-[16px]">call</span>
          <span>1-877-FTC-HELP</span>
        </a>
      </div>
    </header>
  );
}
