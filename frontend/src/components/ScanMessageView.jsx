import React, { useState, useEffect } from 'react';

export default function ScanMessageView({
  message,
  setMessage,
  channel,
  setChannel,
  samplePresets,
  onAnalyze,
  loading,
  result,
  error,
  canRunOffline,
  onRunOffline,
  onClear,
}) {
  const [copiedChecklist, setCopiedChecklist] = useState(false);
  const [copiedResponse, setCopiedResponse] = useState(false);
  const [speaking, setSpeaking] = useState(false);

  // Clean up any ongoing speech synthesis on unmount
  useEffect(() => {
    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
    };
  }, []);

  const handleCopyChecklist = () => {
    if (!result?.safe_next_steps) return;
    navigator.clipboard.writeText(result.safe_next_steps.join('\n• '));
    setCopiedChecklist(true);
    setTimeout(() => setCopiedChecklist(false), 2000);
  };

  const handleCopyResponse = () => {
    if (!result?.suggested_response) return;
    navigator.clipboard.writeText(result.suggested_response);
    setCopiedResponse(true);
    setTimeout(() => setCopiedResponse(false), 2000);
  };

  const handleListenAssessment = () => {
    if (!('speechSynthesis' in window)) {
      alert('Text-to-speech is not supported in this browser.');
      return;
    }

    if (speaking) {
      window.speechSynthesis.cancel();
      setSpeaking(false);
      return;
    }

    if (!result) return;

    const speechScript = `ScamShield Assessment: ${result.risk_level}. Score: ${result.risk_score} out of 100. ${result.summary}. Identified warning signs include: ${result.warning_signs.join(', ')}. Safe advice: ${result.safe_next_steps.slice(0, 2).join('. ')}`;
    const utterance = new SpeechSynthesisUtterance(speechScript);
    utterance.rate = 0.95;
    utterance.onend = () => setSpeaking(false);
    utterance.onerror = () => setSpeaking(false);
    setSpeaking(true);
    window.speechSynthesis.speak(utterance);
  };

  const channels = [
    { id: 'sms', label: 'SMS / Text', icon: 'smartphone' },
    { id: 'email', label: 'Email Alert', icon: 'mail' },
    { id: 'payment_app', label: 'Payment App', icon: 'payments' },
    { id: 'social_media', label: 'Social Chat', icon: 'chat' },
  ];

  return (
    <div className="page-container">
      {/* Hero Header */}
      <div className="page-hero">
        <div className="hero-overline">
          <span className="material-symbols-outlined text-[15px]">security</span>
          Heuristic Inspection Engine
        </div>
        <h2 className="page-title">Inspect Suspicious Message</h2>
        <p className="page-subtitle">
          Pause the pressure. Paste an unverified SMS, email, or urgent payment notice to deconstruct urgency manipulation, brand impersonation, and OTP harvesting threats.
        </p>
      </div>

      {/* Main Analysis Workspace */}
      <div className="analysis-workspace-grid">
        {/* Left Column: Input Panel */}
        <div className="trust-card">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
            <span style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
              1. Select Origin Channel
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--ink-muted)' }}>
              {message.length} / 10,000 chars
            </span>
          </div>

          {/* Channel selector */}
          <div className="channel-pill-group" role="radiogroup" aria-label="Message Channel">
            {channels.map((ch) => (
              <button
                key={ch.id}
                type="button"
                className={`channel-pill ${channel === ch.id ? 'active' : ''}`}
                onClick={() => setChannel(ch.id)}
                role="radio"
                aria-checked={channel === ch.id}
              >
                <span className="material-symbols-outlined text-[16px]">{ch.icon}</span>
                <span>{ch.label}</span>
              </button>
            ))}
          </div>

          {/* Text input */}
          <textarea
            className="clean-textarea"
            placeholder="Paste suspicious message text here... (e.g. 'AMAZON ALERT: Your Prime account has been suspended. Confirm billing within 24 hours at http://amz-prime-support.xyz/login')"
            value={message}
            onChange={(e) => setMessage(e.target.value)}
            maxLength={10000}
            aria-label="Suspicious message input"
          />

          <div className="textarea-meta-row">
            <span>Never share passwords or OTP codes with unverified senders</span>
            <span>Raw text is never saved</span>
          </div>

          {/* Preset Chips */}
          <div className="preset-chips-box">
            <div className="preset-chips-header">
              <span className="material-symbols-outlined text-[16px]">touch_app</span>
              <span>Load Real Test Cases:</span>
            </div>
            <div className="preset-chip-list">
              {samplePresets.map((preset, idx) => (
                <button
                  key={idx}
                  type="button"
                  className="preset-chip"
                  onClick={() => {
                    setMessage(preset.text);
                    if (preset.channel) setChannel(preset.channel);
                  }}
                  title={preset.category}
                >
                  {preset.title}
                </button>
              ))}
            </div>
          </div>

          {/* Error Message */}
          {error && (
            <div style={{
              background: 'var(--risk-high-bg)',
              border: '1px solid var(--risk-high-border)',
              color: 'var(--risk-high-ink)',
              padding: '14px 16px',
              borderRadius: 'var(--radius-md)',
              fontSize: '0.85rem',
              marginBottom: '16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                <span className="material-symbols-outlined text-[18px]">error</span>
                <span>{error}</span>
              </div>
              {canRunOffline && onRunOffline && (
                <button
                  type="button"
                  className="btn-forest-secondary"
                  style={{
                    fontSize: '0.82rem',
                    padding: '8px 14px',
                    alignSelf: 'flex-start',
                    background: '#ffffff',
                    border: '1px solid var(--risk-high-border)',
                    color: 'var(--risk-high-ink)',
                    cursor: 'pointer'
                  }}
                  onClick={onRunOffline}
                >
                  <span className="material-symbols-outlined text-[16px]">offline_bolt</span>
                  <span>Run Offline Analysis (Browser Heuristics Only)</span>
                </button>
              )}
            </div>
          )}

          {/* Action Row */}
          <div style={{ display: 'flex', gap: '12px', marginTop: '16px' }}>
            <button
              type="button"
              className="btn-forest-primary"
              style={{ flex: 1 }}
              onClick={onAnalyze}
              disabled={loading || !message.trim()}
            >
              {loading ? (
                <>
                  <span className="material-symbols-outlined text-[18px] animate-spin">refresh</span>
                  <span>Analyzing Threat Signals...</span>
                </>
              ) : (
                <>
                  <span className="material-symbols-outlined text-[18px]">policy</span>
                  <span>Analyze Message</span>
                </>
              )}
            </button>
            <button
              type="button"
              className="btn-forest-secondary"
              onClick={onClear}
              disabled={loading || !message}
            >
              Clear
            </button>
          </div>
        </div>

        {/* Right Column: Diagnostic & Risk Results */}
        <div className="trust-card" aria-live="polite" aria-atomic="true">
          {!result && !loading && (
            <div style={{ textAlign: 'center', padding: '60px 20px', color: 'var(--ink-muted)' }}>
              <div style={{
                width: '60px',
                height: '60px',
                borderRadius: '50%',
                background: 'var(--surface-low)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                margin: '0 auto 16px',
                color: 'var(--teal-secondary)'
              }}>
                <span className="material-symbols-outlined text-[32px]">shield</span>
              </div>
              <h3 style={{ color: 'var(--forest-primary)', fontSize: '1.15rem', marginBottom: '8px', fontWeight: 700 }}>
                Awaiting Input
              </h3>
              <p style={{ fontSize: '0.88rem', maxWidth: '320px', margin: '0 auto', lineHeight: 1.5 }}>
                Paste an unverified SMS, email, or urgent bill on the left or select a sample case to view explainable risk evaluation.
              </p>
            </div>
          )}

          {loading && (
            <div style={{ textAlign: 'center', padding: '70px 20px', color: 'var(--ink-secondary)' }}>
              <div style={{
                width: '16px',
                height: '16px',
                borderRadius: '50%',
                background: 'var(--teal-secondary)',
                margin: '0 auto 16px',
                boxShadow: '0 0 16px var(--teal-secondary)'
              }} />
              <h3 style={{ color: 'var(--forest-primary)', fontWeight: 700 }}>Running Defensive Heuristics</h3>
              <p style={{ fontSize: '0.82rem', marginTop: '6px' }}>
                Inspecting urgency markers, impersonation signatures, domain authenticity, and OTP requests.
              </p>
            </div>
          )}

          {result && !loading && (
            <div>
              {/* Explicit Offline Simulation Warning */}
              {result.is_offline_simulation && (
                <div style={{
                  background: 'var(--risk-med-bg)',
                  border: '1px solid var(--risk-med-border)',
                  color: 'var(--risk-med-ink)',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  fontSize: '0.8rem',
                  fontWeight: 600,
                  marginBottom: '14px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px'
                }}>
                  <span className="material-symbols-outlined text-[18px]">cloud_off</span>
                  <span>OFFLINE BROWSER SIMULATION: Results evaluated locally using basic browser heuristics without backend threat intelligence or server-grade normalization.</span>
                </div>
              )}

              {/* Risk Banner */}
              <div className={`risk-result-banner ${
                result.risk_level.startsWith('HIGH') ? 'high' :
                result.risk_level.startsWith('ELEVATED') ? 'elevated' : 'low'
              }`}>
                <div>
                  <h3 style={{ fontSize: '1.25rem', fontWeight: 800 }}>{result.risk_level}</h3>
                  <p style={{ fontSize: '0.82rem', marginTop: '4px', opacity: 0.9 }}>{result.summary}</p>
                </div>
                <div className="risk-score-badge">
                  <span className="score-number">{result.risk_score}</span>
                  <span className="score-caption">Score</span>
                </div>
              </div>

              {/* Accessible Speech & Audio Action */}
              <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '14px' }}>
                <button
                  type="button"
                  className={`copy-pill-btn ${speaking ? 'copied' : ''}`}
                  onClick={handleListenAssessment}
                  title="Listen to spoken audio assessment via browser speech synthesis"
                >
                  <span className="material-symbols-outlined text-[16px]">
                    {speaking ? 'volume_up' : 'campaign'}
                  </span>
                  <span>{speaking ? 'Stop Audio' : 'Listen to Assessment'}</span>
                </button>
              </div>

              {/* Strict Caution Disclaimer */}
              <div className="caution-banner" role="note">
                <span className="material-symbols-outlined text-[20px]">warning</span>
                <div>
                  <strong>Notice:</strong> {result.disclaimer}
                </div>
              </div>

              {/* Threat Signals List */}
              <div style={{
                background: 'var(--surface-low)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-lg)',
                padding: '16px',
                marginBottom: '16px'
              }}>
                <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--forest-primary)', marginBottom: '8px' }}>
                  Identified Threat Signals ({result.warning_signs.length})
                </div>
                {result.warning_signs.map((sign, idx) => (
                  <div key={idx} style={{
                    display: 'flex',
                    alignItems: 'flex-start',
                    gap: '8px',
                    fontSize: '0.84rem',
                    padding: '6px 0',
                    borderBottom: '1px solid rgba(0,0,0,0.04)',
                    color: 'var(--ink-primary)'
                  }}>
                    <span style={{ color: 'var(--risk-high-ink)', fontSize: '0.75rem', marginTop: '3px' }}>●</span>
                    <span>{sign}</span>
                  </div>
                ))}
              </div>

              {/* 6-Category Threat Radar */}
              <div className="threat-radar-grid">
                {[
                  { label: 'Urgency Pressure', count: result.breakdown.urgency.length },
                  { label: 'Brand Spoofing', count: result.breakdown.impersonation.length },
                  { label: 'Deceptive Links', count: result.breakdown.suspicious_links.length },
                  { label: 'OTP Code Request', count: result.breakdown.otp_requests.length },
                  { label: 'Payment Pressure', count: result.breakdown.payment_pressure.length },
                  { label: 'Prize/Refund Lure', count: result.breakdown.lures.length },
                ].map((cat, i) => (
                  <div key={i} className={`threat-radar-cell ${cat.count > 0 ? 'flagged' : ''}`}>
                    <div className="threat-radar-header">
                      <span>{cat.label}</span>
                      <span style={{
                        color: cat.count > 0 ? 'var(--risk-high-ink)' : 'var(--ink-muted)',
                        fontWeight: 700
                      }}>
                        {cat.count > 0 ? `Flagged (${cat.count})` : 'Clear'}
                      </span>
                    </div>
                  </div>
                ))}
              </div>

              {/* Recommended Safe Next Steps with Copy */}
              <div className="actionable-subcard">
                <div className="actionable-subcard-header">
                  <span className="subcard-title">
                    <span className="material-symbols-outlined text-[18px]">verified</span>
                    Safe Next Steps
                  </span>
                  <button
                    type="button"
                    className={`copy-pill-btn ${copiedChecklist ? 'copied' : ''}`}
                    onClick={handleCopyChecklist}
                  >
                    <span className="material-symbols-outlined text-[14px]">
                      {copiedChecklist ? 'check' : 'content_copy'}
                    </span>
                    <span>{copiedChecklist ? 'Copied' : 'Copy Checklist'}</span>
                  </button>
                </div>
                <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: '8px', fontSize: '0.82rem', color: 'var(--ink-secondary)' }}>
                  {result.safe_next_steps.map((step, idx) => (
                    <li key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                      <span style={{ color: 'var(--teal-secondary)', fontWeight: 700 }}>✓</span>
                      <span>{step}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Suggested Safe Response with Copy */}
              <div className="actionable-subcard">
                <div className="actionable-subcard-header">
                  <span className="subcard-title">
                    <span className="material-symbols-outlined text-[18px]">chat</span>
                    Suggested Protective Reply
                  </span>
                  <button
                    type="button"
                    className={`copy-pill-btn ${copiedResponse ? 'copied' : ''}`}
                    onClick={handleCopyResponse}
                  >
                    <span className="material-symbols-outlined text-[14px]">
                      {copiedResponse ? 'check' : 'content_copy'}
                    </span>
                    <span>{copiedResponse ? 'Copied' : 'Copy Reply'}</span>
                  </button>
                </div>
                <div style={{
                  fontSize: '0.82rem',
                  color: 'var(--ink-secondary)',
                  background: '#ffffff',
                  border: '1px solid var(--border-subtle)',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md)',
                  fontStyle: 'italic',
                  lineHeight: 1.5
                }}>
                  "{result.suggested_response}"
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
