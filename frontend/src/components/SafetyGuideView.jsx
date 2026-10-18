import React, { useState, useEffect, useCallback } from 'react';
import { API_BASE } from '../config';

export default function SafetyGuideView() {
  const [searchQuery, setSearchQuery] = useState('');
  const [checkedSteps, setCheckedSteps] = useState([false, false, false, false, false]);
  const [copiedLink, setCopiedLink] = useState(false);
  const [backendResources, setBackendResources] = useState({
    emergency_guidance: [],
    general_checklist: [],
    reporting_resources: {},
  });

  const fetchSafetyResources = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/api/v1/safe-next-steps`);
      if (res.ok) {
        const data = await res.json();
        setBackendResources(data);
      }
    } catch {
      // Offline fallback
    }
  }, []);

  useEffect(() => {
    fetchSafetyResources();
  }, [fetchSafetyResources]);

  const principles = [
    {
      num: '01',
      title: 'Pause the Pressure',
      subtitle: 'The Golden Protective Habit',
      icon: 'hourglass_top',
      keywords: 'pressure urgency hurry emergency deadline arrest 1 hour calm golden rule',
      why: 'Scammers manufacture artificial deadlines ("within 1 hour", "immediate account suspension") specifically to bypass critical judgment and trigger fear.',
      move: 'Step back and breathe. Any legitimate institutional communication can wait 10 minutes while you verify through an independent channel.',
      rule: 'Zero Urgency Rule',
    },
    {
      num: '02',
      title: 'Never Share OTPs or Passwords',
      subtitle: 'The Sacred Key Boundary',
      icon: 'key',
      keywords: 'otp password 2fa two-factor code authentication bank verification sms credentials',
      why: 'One-Time Passwords (OTPs) and 2-factor codes are designed strictly for user-to-system verification. Fraudsters pose as support staff to intercept them.',
      move: 'No genuine bank, technology company, or government agency will ever ask you to read back or forward an SMS verification code.',
      rule: 'Strict Zero-Share',
    },
    {
      num: '03',
      title: 'Verify Independently',
      subtitle: 'Bypass Caller ID Spoofing',
      icon: 'call_end',
      keywords: 'verify independently caller id spoofing official website back of card phone number hang up',
      why: 'Modern VoIP telephony makes it trivial for attackers to falsify caller ID names to display your bank’s name or police precinct numbers.',
      move: 'Hang up. Locate the official phone number printed on the back of your physical debit or credit card, or open a clean browser and visit the verified portal.',
      rule: 'Out-of-Band Verification',
    },
    {
      num: '04',
      title: 'Beware Untrusted Links',
      subtitle: 'Inspect the True Domain',
      icon: 'link_off',
      keywords: 'links urls typos text sms delivery parcel tracking postal usps fedex dhl clicks',
      why: 'Deceptive messages often route recipients to lookalike portals hosted on unverified top-level domains that clone real login pages.',
      move: 'Avoid tapping links sent in unsolicited text messages. Navigate directly to the organization’s verified application or main website.',
      rule: 'Direct Address Navigation',
    },
    {
      num: '05',
      title: 'Family Safe-Word Agreement',
      subtitle: 'Counteract AI Audio Cloning',
      icon: 'record_voice_over',
      keywords: 'family emergency ai voice audio cloning deepfake grandchild grandparent bail jail hospital secret code word',
      why: 'AI voice synthesizers can mimic family members using brief audio snippets. Scammers use this in distress and kidnapping impersonation scams.',
      move: 'Establish a secret family challenge word. If a distress call arrives demanding money, ask for the family word, hang up, and call their direct phone.',
      rule: 'Family Challenge Phrase',
    },
    {
      num: '06',
      title: 'Gift Cards & Crypto Demands = Fraud',
      subtitle: 'Definitive Warning Signal',
      icon: 'credit_card_off',
      keywords: 'gift cards crypto cryptocurrency bitcoin apple target zelle payment wire irs fines fraud',
      why: 'Gift cards, cryptocurrency transfers, and peer-to-peer payments are immediate, untraceable, and cannot be refunded by banking networks.',
      move: 'No legitimate government department (IRS, SSA, police) or major retailer will ever mandate payment via gift cards or Bitcoin kiosks.',
      rule: 'Immediate Disqualification',
    },
  ];

  const filteredPrinciples = principles.filter((p) => {
    if (!searchQuery) return true;
    const q = searchQuery.toLowerCase().trim();
    return (
      p.title.toLowerCase().includes(q) ||
      p.subtitle.toLowerCase().includes(q) ||
      p.keywords.toLowerCase().includes(q) ||
      p.why.toLowerCase().includes(q) ||
      p.move.toLowerCase().includes(q)
    );
  });

  const toggleStep = (idx) => {
    const updated = [...checkedSteps];
    updated[idx] = !updated[idx];
    setCheckedSteps(updated);
  };

  const completedSteps = checkedSteps.filter(Boolean).length;
  const progressPercent = Math.round((completedSteps / checkedSteps.length) * 100);

  const handleShare = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopiedLink(true);
    setTimeout(() => setCopiedLink(false), 2000);
  };

  return (
    <div className="page-container">
      {/* Overline & Title */}
      <div className="page-hero">
        <div className="hero-overline">
          <span className="material-symbols-outlined text-[15px]">verified_user</span>
          Protective Guidance
        </div>
        <h2 className="page-title">ScamShield Safety Guide</h2>
        <p className="page-subtitle">
          Structured defensive rules and emergency triage instructions. Learn how social engineering leverages artificial urgency.
        </p>

        {/* Search Bar */}
        <div style={{ marginTop: '20px', position: 'relative' }}>
          <div style={{
            display: 'flex',
            alignItems: 'center',
            background: '#ffffff',
            border: '1.5px solid var(--border-subtle)',
            borderRadius: 'var(--radius-lg)',
            padding: '4px 16px',
            boxShadow: 'var(--shadow-sm)'
          }}>
            <span className="material-symbols-outlined text-[20px]" style={{ color: 'var(--ink-muted)', marginRight: '10px' }}>
              search
            </span>
            <input
              type="text"
              placeholder="Search tactics (e.g. OTP code, delivery fee, gift cards, voice cloning, IRS)..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={{
                width: '100%',
                border: 'none',
                outline: 'none',
                fontFamily: 'var(--font-body)',
                fontSize: '0.92rem',
                color: 'var(--ink-primary)',
                padding: '10px 0'
              }}
              aria-label="Search safety tactics"
            />
            {searchQuery && (
              <button
                type="button"
                onClick={() => setSearchQuery('')}
                style={{
                  background: 'transparent',
                  border: 'none',
                  color: 'var(--ink-muted)',
                  cursor: 'pointer'
                }}
                aria-label="Clear search query"
              >
                <span className="material-symbols-outlined text-[18px]">close</span>
              </button>
            )}
          </div>

          {/* Quick jump filter chips */}
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: '8px', marginTop: '12px', alignItems: 'center' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--ink-muted)' }}>QUICK FILTERS:</span>
            {['Urgency', 'OTP', 'Voice Cloning', 'Gift Cards', 'Recovery'].map((filter) => (
              <button
                key={filter}
                type="button"
                className="preset-chip"
                onClick={() => setSearchQuery(filter)}
              >
                {filter}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Human-First Reality Banner (No fake percentages) */}
      <div style={{
        background: 'var(--surface-low)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-xl)',
        padding: '24px 28px',
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '20px',
        marginBottom: '32px'
      }}>
        <div style={{ maxWidth: '640px' }}>
          <div style={{
            fontSize: '0.74rem',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--teal-secondary)',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            marginBottom: '6px'
          }}>
            <span className="material-symbols-outlined text-[16px]">lightbulb</span>
            Core Awareness
          </div>
          <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', fontWeight: 700, color: 'var(--forest-primary)', lineHeight: 1.4 }}>
            "Social engineering exploits urgency, compliance, and empathy rather than technical vulnerabilities."
          </p>
          <p style={{ fontSize: '0.85rem', color: 'var(--ink-secondary)', marginTop: '4px' }}>
            Taking time to cross-verify out-of-band neutralizes high-pressure tactics.
          </p>
        </div>

        <div style={{
          background: '#ffffff',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-lg)',
          padding: '14px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: '14px',
          boxShadow: 'var(--shadow-sm)'
        }}>
          <div style={{
            width: '42px',
            height: '42px',
            borderRadius: 'var(--radius-md)',
            background: 'var(--surface-low)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--teal-secondary)'
          }}>
            <span className="material-symbols-outlined text-[24px]">timer</span>
          </div>
          <div>
            <div style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--ink-muted)', textTransform: 'uppercase' }}>
              RECOMMENDED HABIT
            </div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.15rem', fontWeight: 800, color: 'var(--forest-primary)' }}>
              10-Minute Pause
            </div>
            <div style={{ fontSize: '0.75rem', color: 'var(--teal-secondary)', fontWeight: 600 }}>
              Verify before responding
            </div>
          </div>
        </div>
      </div>

      {/* 6 Core Defense Principles Bento Grid */}
      <div style={{ marginBottom: '40px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--teal-secondary)' }}>
              CORE PRINCIPLES
            </span>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.45rem', fontWeight: 800, color: 'var(--forest-primary)' }}>
              Defensive Best Practices
            </h3>
          </div>
          <span style={{ fontSize: '0.82rem', color: 'var(--ink-muted)' }}>
            {filteredPrinciples.length} of 6 shown
          </span>
        </div>

        <div className="principles-grid">
          {filteredPrinciples.map((p) => (
            <div key={p.num} className="principle-card">
              <div>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '14px' }}>
                  <div style={{
                    width: '44px',
                    height: '44px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--surface-mint)',
                    color: 'var(--teal-secondary)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center'
                  }}>
                    <span className="material-symbols-outlined text-[24px]">{p.icon}</span>
                  </div>
                  <span style={{
                    fontSize: '0.72rem',
                    fontWeight: 700,
                    padding: '3px 10px',
                    borderRadius: 'var(--radius-full)',
                    background: 'var(--surface-low)',
                    color: 'var(--ink-secondary)'
                  }}>
                    Principle {p.num}
                  </span>
                </div>

                <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.15rem', fontWeight: 700, color: 'var(--forest-primary)', marginBottom: '4px' }}>
                  {p.title}
                </h4>
                <div style={{ fontSize: '0.8rem', color: 'var(--teal-secondary)', fontWeight: 600, marginBottom: '12px' }}>
                  {p.subtitle}
                </div>

                {/* Why it works */}
                <div style={{
                  background: 'var(--surface-low)',
                  borderRadius: 'var(--radius-md)',
                  padding: '10px 12px',
                  fontSize: '0.8rem',
                  color: 'var(--ink-secondary)',
                  marginBottom: '10px'
                }}>
                  <div style={{ fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--ink-muted)', marginBottom: '3px' }}>
                    WHY IT OCCURS
                  </div>
                  {p.why}
                </div>

                {/* Your move */}
                <div style={{
                  background: 'var(--surface-mint)',
                  borderRadius: 'var(--radius-md)',
                  padding: '10px 12px',
                  fontSize: '0.8rem',
                  color: 'var(--forest-primary)'
                }}>
                  <div style={{ fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--teal-secondary)', marginBottom: '3px' }}>
                    RECOMMENDED ACTION
                  </div>
                  {p.move}
                </div>
              </div>

              <div style={{
                marginTop: '16px',
                paddingTop: '12px',
                borderTop: '1px solid var(--border-subtle)',
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                fontSize: '0.75rem',
                color: 'var(--ink-muted)'
              }}>
                <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--teal-secondary)' }} />
                  {p.rule}
                </span>
                <span className="material-symbols-outlined text-[16px]">verified</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Interactive 5-Step Incident Response Checklist */}
      <div className="trust-card" style={{ marginBottom: '40px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px', marginBottom: '20px' }}>
          <div>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '3px 10px',
              borderRadius: 'var(--radius-full)',
              background: 'var(--risk-high-bg)',
              color: 'var(--risk-high-ink)',
              fontSize: '0.72rem',
              fontWeight: 700,
              textTransform: 'uppercase',
              marginBottom: '6px'
            }}>
              <span className="material-symbols-outlined text-[14px]">emergency</span>
              Immediate Incident Recovery Sequence
            </span>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.4rem', fontWeight: 800, color: 'var(--forest-primary)' }}>
              What to do if you suspect you already responded
            </h3>
            <p style={{ fontSize: '0.88rem', color: 'var(--ink-secondary)', marginTop: '4px' }}>
              Acting promptly limits potential access and financial exposure.
            </p>
          </div>

          {/* Progress dial */}
          <div style={{
            background: 'var(--surface-low)',
            padding: '12px 18px',
            borderRadius: 'var(--radius-lg)',
            display: 'flex',
            alignItems: 'center',
            gap: '14px'
          }}>
            <div style={{ position: 'relative', width: '48px', height: '48px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg className="w-12 h-12 transform -rotate-90" viewBox="0 0 36 36" style={{ width: '48px', height: '48px' }}>
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="#e2e0d8"
                  strokeWidth="3.2"
                />
                <path
                  d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                  fill="none"
                  stroke="var(--teal-secondary)"
                  strokeWidth="3.2"
                  strokeDasharray={`${progressPercent}, 100`}
                  strokeLinecap="round"
                />
              </svg>
              <span style={{ position: 'absolute', fontSize: '0.74rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
                {completedSteps}/5
              </span>
            </div>
            <div>
              <div style={{ fontSize: '0.68rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--ink-muted)' }}>
                CHECKLIST PROGRESS
              </div>
              <div style={{ fontSize: '0.86rem', fontWeight: 700, color: completedSteps === 5 ? 'var(--teal-secondary)' : 'var(--forest-primary)' }}>
                {completedSteps === 0 ? 'Ready' : completedSteps === 5 ? 'All Completed' : `${progressPercent}% Completed`}
              </div>
            </div>
          </div>
        </div>

        {/* 5 Steps */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
          {[
            {
              time: 'Immediate',
              title: 'Step 1: Sever Communication Instantly',
              desc: 'Hang up immediately. Block the phone number. If you installed remote software (e.g. AnyDesk, TeamViewer), disconnect your Wi-Fi or turn off the device.',
            },
            {
              time: 'Minutes Count',
              title: 'Step 2: Lock Compromised Cards via App',
              desc: 'Open your banking application and toggle the "Lock / Freeze Card" switch for any debit or credit accounts mentioned.',
            },
            {
              time: 'Urgent',
              title: 'Step 3: Update Core Passwords from a Clean Device',
              desc: 'Using a separate phone or family computer, change the password for your primary email and banking portal. Sign out of all active remote sessions.',
            },
            {
              time: 'Follow-up',
              title: 'Step 4: File Reports with Official Regulatory Agencies',
              desc: 'Submit fraud details directly to IdentityTheft.gov and ReportFraud.ftc.gov to document the incident.',
            },
            {
              time: 'Support',
              title: 'Step 5: Talk with Someone You Trust',
              desc: 'Scams frequently thrive on secrecy. Sharing what occurred with a friend, family member, or consumer advocate reduces stress and clarifies next steps.',
            },
          ].map((step, idx) => (
            <label
              key={idx}
              style={{
                display: 'flex',
                alignItems: 'flex-start',
                gap: '14px',
                padding: '14px 18px',
                borderRadius: 'var(--radius-lg)',
                background: checkedSteps[idx] ? 'var(--surface-mint)' : 'var(--surface-low)',
                border: '1px solid var(--border-subtle)',
                cursor: 'pointer',
                transition: 'background 0.15s ease'
              }}
            >
              <input
                type="checkbox"
                checked={checkedSteps[idx]}
                onChange={() => toggleStep(idx)}
                style={{ width: '18px', height: '18px', marginTop: '2px', accentColor: 'var(--forest-primary)', cursor: 'pointer' }}
              />
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.9rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
                    {step.title}
                  </span>
                  <span style={{ fontSize: '0.72rem', fontWeight: 600, color: 'var(--ink-muted)' }}>
                    {step.time}
                  </span>
                </div>
                <p style={{ fontSize: '0.82rem', color: 'var(--ink-secondary)', marginTop: '2px' }}>
                  {step.desc}
                </p>
              </div>
            </label>
          ))}
        </div>
      </div>

      {/* Verified Backend Reporting Portals (Loaded from /api/v1/safe-next-steps) */}
      <div style={{ marginBottom: '40px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
          <div>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em', color: 'var(--teal-secondary)' }}>
              OFFICIAL CHANNELS
            </span>
            <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.45rem', fontWeight: 800, color: 'var(--forest-primary)' }}>
              Verified Reporting Portals
            </h3>
          </div>
          <span style={{ fontSize: '0.8rem', color: 'var(--ink-muted)' }}>
            Loaded from ScamShield API
          </span>
        </div>

        <div className="trust-card">
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '12px' }}>
            {Object.entries(backendResources.reporting_resources).map(([portalName, url], idx) => (
              <div
                key={idx}
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  padding: '12px 14px',
                  background: 'var(--surface-low)',
                  borderRadius: 'var(--radius-md)'
                }}
              >
                <div>
                  <div style={{ fontSize: '0.86rem', fontWeight: 600, color: 'var(--ink-primary)' }}>{portalName}</div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--ink-muted)', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap', maxWidth: '200px' }}>
                    {url}
                  </div>
                </div>
                <a
                  href={url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="copy-pill-btn"
                  title={`Open official portal: ${portalName}`}
                >
                  <span className="material-symbols-outlined text-[16px]">open_in_new</span>
                  <span>Visit</span>
                </a>
              </div>
            ))}
          </div>

          <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', fontSize: '0.78rem', color: 'var(--ink-muted)' }}>
            For banking concerns, always consult the customer service telephone number printed directly on the back of your physical payment card.
          </div>
        </div>
      </div>

      {/* Share / Print Card */}
      <div style={{
        background: 'var(--forest-primary)',
        color: '#ffffff',
        borderRadius: 'var(--radius-xl)',
        padding: '24px 28px',
        display: 'flex',
        flexWrap: 'wrap',
        justifyContent: 'space-between',
        alignItems: 'center',
        gap: '16px'
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
          <div style={{ width: '44px', height: '44px', borderRadius: 'var(--radius-md)', background: 'var(--forest-container)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <span className="material-symbols-outlined text-[24px]">print</span>
          </div>
          <div>
            <div style={{ fontSize: '1rem', fontWeight: 700 }}>Printable Reference Copy</div>
            <div style={{ fontSize: '0.8rem', opacity: 0.8 }}>Generate a clean, high-contrast reference copy for personal or family review.</div>
          </div>
        </div>

        <div style={{ display: 'flex', gap: '10px' }}>
          <button
            type="button"
            className="btn-forest-secondary"
            style={{ background: '#ffffff', color: 'var(--forest-primary)' }}
            onClick={() => window.print()}
          >
            <span className="material-symbols-outlined text-[16px]">print</span>
            <span>Print Guide</span>
          </button>
          <button
            type="button"
            className="btn-forest-secondary"
            style={{ background: 'var(--forest-container)', color: '#ffffff', borderColor: 'rgba(255,255,255,0.2)' }}
            onClick={handleShare}
          >
            <span className="material-symbols-outlined text-[16px]">
              {copiedLink ? 'done' : 'share'}
            </span>
            <span>{copiedLink ? 'Link Copied!' : 'Share Guide'}</span>
          </button>
        </div>
      </div>
    </div>
  );
}
