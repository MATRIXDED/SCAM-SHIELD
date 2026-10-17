import React from 'react';

export default function RecentChecksView({ history, loading, onRefresh, backendStatus }) {
  return (
    <div className="page-container">
      <div className="page-hero">
        <div className="hero-overline">
          <span className="material-symbols-outlined text-[15px]">history</span>
          Telemetry Audit Log
        </div>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
          <div>
            <h2 className="page-title">Recent Checks History</h2>
            <p className="page-subtitle">
              Audit log of verified communications. In compliance with privacy safeguards, only cryptographic SHA-256 fingerprints and risk metrics are stored.
            </p>
          </div>
          <button
            type="button"
            className="btn-forest-secondary"
            onClick={onRefresh}
            disabled={loading}
          >
            <span className="material-symbols-outlined text-[16px]">refresh</span>
            <span>Refresh Audit Log</span>
          </button>
        </div>
      </div>

      {/* Privacy Guarantee Banner */}
      <div style={{
        background: 'var(--surface-mint)',
        border: '1px solid var(--risk-low-border)',
        borderRadius: 'var(--radius-lg)',
        padding: '14px 18px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        marginBottom: '24px',
        fontSize: '0.84rem',
        color: 'var(--forest-primary)'
      }}>
        <span className="material-symbols-outlined text-[20px]" style={{ color: 'var(--teal-secondary)' }}>
          verified_user
        </span>
        <div>
          <strong>Privacy Safeguard:</strong> Raw message contents and sensitive details are processed in volatile memory. 
          When telemetry logging is enabled, only an anonymized SHA-256 fingerprint and summary scores are saved to the active database (
          <strong>{backendStatus?.mode === 'supabase_cloud' ? 'Supabase Cloud PostgreSQL' : 'Local SQLite database'}</strong>
          ).
        </div>
      </div>

      {/* History Table Card */}
      <div className="trust-card">
        {loading ? (
          <div style={{ textAlign: 'center', padding: '40px', color: 'var(--ink-secondary)' }}>
            <span className="material-symbols-outlined text-[24px] animate-spin">refresh</span>
            <p style={{ marginTop: '8px', fontSize: '0.85rem' }}>Loading telemetry records...</p>
          </div>
        ) : history.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '50px 20px', color: 'var(--ink-muted)' }}>
            <span className="material-symbols-outlined text-[32px]">manage_search</span>
            <h3 style={{ fontSize: '1.05rem', color: 'var(--forest-primary)', marginTop: '8px', fontWeight: 700 }}>
              No Prior Checks Logged
            </h3>
            <p style={{ fontSize: '0.84rem', maxWidth: '340px', margin: '4px auto 0' }}>
              When you evaluate suspicious messages with history logging enabled, anonymized telemetry hashes appear here.
            </p>
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.84rem' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid var(--border-subtle)', textAlign: 'left', color: 'var(--ink-muted)' }}>
                  <th style={{ padding: '12px 14px', fontWeight: 600 }}>SHA-256 Fingerprint</th>
                  <th style={{ padding: '12px 14px', fontWeight: 600 }}>Risk Classification</th>
                  <th style={{ padding: '12px 14px', fontWeight: 600 }}>Score</th>
                  <th style={{ padding: '12px 14px', fontWeight: 600 }}>Channel</th>
                  <th style={{ padding: '12px 14px', fontWeight: 600 }}>Flags</th>
                  <th style={{ padding: '12px 14px', fontWeight: 600 }}>Logged At</th>
                </tr>
              </thead>
              <tbody>
                {history.map((item) => (
                  <tr key={item.id} style={{ borderBottom: '1px solid rgba(0,0,0,0.04)' }}>
                    <td style={{ padding: '12px 14px' }}>
                      <span style={{
                        fontFamily: 'var(--font-mono)',
                        fontSize: '0.75rem',
                        background: 'var(--surface-low)',
                        padding: '3px 8px',
                        borderRadius: '4px',
                        color: 'var(--teal-secondary)'
                      }}>
                        {item.fingerprint.substring(0, 16)}...
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px', fontWeight: 700 }}>
                      <span style={{
                        padding: '3px 8px',
                        borderRadius: 'var(--radius-full)',
                        fontSize: '0.72rem',
                        background: item.risk_level.startsWith('HIGH') ? 'var(--risk-high-bg)' : item.risk_level.startsWith('ELEVATED') ? 'var(--risk-med-bg)' : 'var(--risk-low-bg)',
                        color: item.risk_level.startsWith('HIGH') ? 'var(--risk-high-ink)' : item.risk_level.startsWith('ELEVATED') ? 'var(--risk-med-ink)' : 'var(--risk-low-ink)',
                        border: '1px solid',
                        borderColor: item.risk_level.startsWith('HIGH') ? 'var(--risk-high-border)' : item.risk_level.startsWith('ELEVATED') ? 'var(--risk-med-border)' : 'var(--risk-low-border)'
                      }}>
                        {item.risk_level}
                      </span>
                    </td>
                    <td style={{ padding: '12px 14px', fontWeight: 700, color: 'var(--forest-primary)' }}>
                      {item.risk_score} / 100
                    </td>
                    <td style={{ padding: '12px 14px', textTransform: 'capitalize', color: 'var(--ink-secondary)' }}>
                      {item.channel}
                    </td>
                    <td style={{ padding: '12px 14px', color: 'var(--ink-secondary)' }}>
                      {item.warning_count} flags
                    </td>
                    <td style={{ padding: '12px 14px', fontSize: '0.78rem', color: 'var(--ink-muted)' }}>
                      {new Date(item.created_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
