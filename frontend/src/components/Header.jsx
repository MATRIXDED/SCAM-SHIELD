import React from 'react';

export default function Header({ activeTab, setActiveTab, backendStatus }) {
  const tabTitles = {
    scan: 'Safety Inspection',
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
          Prototype — Simulated Data Only
        </span>
      </div>

      <div className="header-right">
        <div className={`status-badge-live ${backendStatus.supabase_configured ? '' : 'demo'}`}>
          <span className="live-dot" />
          <span>{backendStatus.supabase_configured ? 'Supabase Cloud' : 'Local SQLite Demo'}</span>
        </div>

        {setActiveTab && (
          <button
            type="button"
            className="btn-forest-secondary"
            style={{ padding: '6px 14px', fontSize: '0.8rem', borderRadius: 'var(--radius-md)' }}
            onClick={() => setActiveTab('guide')}
            title="Read foundational defense principles and recovery steps"
          >
            <span className="material-symbols-outlined text-[16px]" style={{ color: 'var(--teal-secondary)' }}>
              visibility
            </span>
            <span>How this check works</span>
          </button>
        )}

        <a
          href="tel:1930"
          className="helpline-link"
          title="Official India National Cyber Financial Fraud Helpline (24/7): Dial 1930"
        >
          <span className="material-symbols-outlined text-[16px]">call</span>
          <span>India Cyber Helpline: 1930</span>
        </a>

        <div
          style={{
            width: '34px',
            height: '34px',
            borderRadius: '50%',
            background: 'var(--forest-primary)',
            color: '#ffffff',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            marginLeft: '4px',
          }}
          aria-hidden="true"
        >
          <span className="material-symbols-outlined text-[18px]">person</span>
        </div>
      </div>
    </header>
  );
}

