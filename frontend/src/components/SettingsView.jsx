import React from 'react';

export default function SettingsView({ backendStatus, onRefreshStatus }) {
  return (
    <div className="page-container">
      <div className="page-hero">
        <div className="hero-overline">
          <span className="material-symbols-outlined text-[15px]">settings</span>
          Diagnostics &amp; Security Architecture
        </div>
        <h2 className="page-title">System &amp; Privacy Diagnostics</h2>
        <p className="page-subtitle">
          Verify live backend telemetry connections, cryptographic isolation guarantees, and Alexa+ MCP track interfaces.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px' }}>
        {/* Backend & Persistence Diagnostics */}
        <div className="trust-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
            <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
              Storage &amp; Cloud Status
            </h3>
            <button
              type="button"
              className="copy-pill-btn"
              onClick={onRefreshStatus}
              title="Poll /api/v1/status"
            >
              <span className="material-symbols-outlined text-[14px]">refresh</span>
              <span>Re-check</span>
            </button>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', fontSize: '0.84rem' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--surface-low)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ color: 'var(--ink-secondary)' }}>Operating Mode:</span>
              <strong style={{ color: backendStatus.supabase_configured ? 'var(--teal-secondary)' : 'var(--forest-primary)' }}>
                {backendStatus.mode === 'supabase_cloud' ? 'Supabase Cloud (PostgreSQL)' : 'Local Zero-Storage Demo (SQLite)'}
              </strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--surface-low)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ color: 'var(--ink-secondary)' }}>Supabase Credentials:</span>
              <strong>{backendStatus.supabase_configured ? 'Configured (Active)' : 'Unset (Using Local Sandbox)'}</strong>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--surface-low)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ color: 'var(--ink-secondary)' }}>Privacy Policy:</span>
              <span style={{ color: 'var(--teal-secondary)', fontWeight: 600 }}>Zero Raw Message Persistence</span>
            </div>

            <div style={{ display: 'flex', justifyContent: 'space-between', padding: '8px 12px', background: 'var(--surface-low)', borderRadius: 'var(--radius-md)' }}>
              <span style={{ color: 'var(--ink-secondary)' }}>Target Database:</span>
              <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem' }}>
                {backendStatus.storage_target || 'backend/teampilot.db'}
              </code>
            </div>
          </div>
        </div>

        {/* Amazon Alexa+ MCP Architecture */}
        <div className="trust-card">
          <h3 style={{ fontSize: '1.1rem', fontWeight: 700, color: 'var(--forest-primary)', marginBottom: '8px' }}>
            Amazon Alexa+ MCP Architecture
          </h3>
          <p style={{ fontSize: '0.84rem', color: 'var(--ink-secondary)', lineHeight: 1.5, marginBottom: '14px' }}>
            ScamShield provides a compliant Model Context Protocol (MCP) server under <code style={{ fontFamily: 'var(--font-mono)' }}>mcp_server/server.py</code> for assistant tool calling and automated analysis.
          </p>

          <div style={{
            background: 'var(--surface-low)',
            borderRadius: 'var(--radius-md)',
            padding: '12px 14px',
            fontSize: '0.78rem',
            fontFamily: 'var(--font-mono)',
            color: 'var(--forest-primary)',
            lineHeight: 1.6
          }}>
            <div>// Test MCP JSON-RPC 2.0 tools:</div>
            <div style={{ fontWeight: 700 }}>python mcp_server/server.py --test</div>
            <div style={{ marginTop: '6px', color: 'var(--ink-muted)' }}>// Exposed tools:</div>
            <div>• analyze_suspicious_message</div>
            <div>• get_safe_next_steps</div>
            <div>• get_sample_threat_cases</div>
          </div>
        </div>
      </div>
    </div>
  );
}
