import React, { useState } from 'react';

export default function FamilySafetyView() {
  const [safeWord, setSafeWord] = useState('');
  const [savedWord, setSavedWord] = useState('');
  const [simulatedAlertTriggered, setSimulatedAlertTriggered] = useState(false);

  const handleSaveWord = (e) => {
    e.preventDefault();
    if (safeWord.trim()) {
      setSavedWord(safeWord.trim());
      setSafeWord('');
    }
  };

  const handleSimulateAlert = () => {
    setSimulatedAlertTriggered(true);
    setTimeout(() => setSimulatedAlertTriggered(false), 4500);
  };

  return (
    <div className="page-container">
      <div className="page-hero">
        <div className="hero-overline">
          <span className="material-symbols-outlined text-[15px]">family_restroom</span>
          Family Defense Strategy
        </div>
        <h2 className="page-title">Family Safety &amp; Safe-Word Protocol</h2>
        <p className="page-subtitle">
          Proactive psychological protection against AI audio cloning, distress calls, and grandparent impersonation.
        </p>
      </div>

      {/* Mandatory Simulation Notice Banner */}
      <div style={{
        background: 'var(--risk-med-bg)',
        border: '1px solid var(--risk-med-border)',
        borderRadius: 'var(--radius-lg)',
        padding: '14px 18px',
        display: 'flex',
        alignItems: 'center',
        gap: '12px',
        marginBottom: '24px',
        fontSize: '0.84rem',
        color: 'var(--risk-med-ink)'
      }}>
        <span className="material-symbols-outlined text-[20px]">info</span>
        <div>
          <strong>Simulation Sandbox:</strong> The alert relay below is an interactive hackathon simulation. No real telecommunications carrier SMS or emergency services dispatch is performed.
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px' }}>
        {/* Safe-Word Agreement Card */}
        <div className="trust-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
            <span className="material-symbols-outlined text-[24px]" style={{ color: 'var(--teal-secondary)' }}>
              key
            </span>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
              1. The Family Challenge Phrase
            </h3>
          </div>
          <p style={{ fontSize: '0.84rem', color: 'var(--ink-secondary)', marginBottom: '16px', lineHeight: 1.5 }}>
            Because AI voice synthesizers can mimic family members using short audio clips, an unwritten safe-word or childhood memory is a reliable verbal authentication factor.
          </p>

          <form onSubmit={handleSaveWord} style={{ display: 'flex', gap: '10px', marginBottom: '16px' }}>
            <input
              type="text"
              placeholder="e.g. Grandma's Lemon Cake"
              value={safeWord}
              onChange={(e) => setSafeWord(e.target.value)}
              style={{
                flex: 1,
                padding: '10px 14px',
                border: '1.5px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                fontFamily: 'var(--font-body)',
                fontSize: '0.88rem',
                outline: 'none'
              }}
              aria-label="Family safe word input"
            />
            <button type="submit" className="btn-forest-primary" style={{ padding: '10px 18px', fontSize: '0.86rem' }}>
              Set Safe Word
            </button>
          </form>

          {savedWord && (
            <div style={{
              background: 'var(--surface-mint)',
              border: '1px solid var(--risk-low-border)',
              borderRadius: 'var(--radius-md)',
              padding: '12px 14px',
              fontSize: '0.82rem',
              color: 'var(--forest-primary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between'
            }}>
              <span>Active Challenge Phrase: <strong>"{savedWord}"</strong></span>
              <button
                type="button"
                onClick={() => setSavedWord('')}
                style={{ background: 'transparent', border: 'none', color: 'var(--ink-muted)', cursor: 'pointer', fontSize: '0.75rem' }}
              >
                Clear
              </button>
            </div>
          )}
        </div>

        {/* Simulated Incident Broadcast Sandbox */}
        <div className="trust-card">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px', marginBottom: '14px' }}>
            <span className="material-symbols-outlined text-[24px]" style={{ color: 'var(--forest-primary)' }}>
              notification_important
            </span>
            <h3 style={{ fontSize: '1.15rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
              2. Simulated Family Circle Alert
            </h3>
          </div>
          <p style={{ fontSize: '0.84rem', color: 'var(--ink-secondary)', marginBottom: '16px', lineHeight: 1.5 }}>
            Test how an automated alert would appear to a trusted circle if a family member reports an extortion or urgent financial coercion attempt.
          </p>

          <div style={{
            background: 'var(--surface-low)',
            borderRadius: 'var(--radius-lg)',
            padding: '16px',
            marginBottom: '16px',
            fontSize: '0.8rem',
            color: 'var(--ink-secondary)'
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '6px' }}>
              <span>Delivery Pipeline:</span>
              <span style={{ fontWeight: 600 }}>Simulated Local Event Bus</span>
            </div>
            <div style={{ display: 'flex', justifyContent: 'space-between' }}>
              <span>Live Carrier SMS:</span>
              <span style={{ color: 'var(--ink-muted)' }}>Disabled (Hackathon Demo)</span>
            </div>
          </div>

          <button
            type="button"
            className="btn-forest-primary"
            style={{ width: '100%', background: 'var(--forest-container)' }}
            onClick={handleSimulateAlert}
            disabled={simulatedAlertTriggered}
          >
            <span className="material-symbols-outlined text-[18px]">cell_tower</span>
            <span>
              {simulatedAlertTriggered ? 'Simulated Alert Broadcast Active...' : 'Simulate Family Circle Alert'}
            </span>
          </button>

          {simulatedAlertTriggered && (
            <div style={{
              marginTop: '12px',
              padding: '10px 14px',
              background: 'var(--surface-mint)',
              border: '1px solid var(--risk-low-border)',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.8rem',
              color: 'var(--forest-primary)',
              display: 'flex',
              alignItems: 'center',
              gap: '8px'
            }}>
              <span className="material-symbols-outlined text-[16px]">check_circle</span>
              <span>[SIMULATED] Mock notification dispatched in local sandbox.</span>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
