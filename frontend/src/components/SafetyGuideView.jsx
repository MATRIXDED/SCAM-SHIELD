import React, { useState, useEffect } from 'react';
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

  // Fetch verified resources from backend API
  useEffect(() => {
    let active = true;
    fetch(`${API_BASE}/api/v1/safe-next-steps`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (active && data) {
          setBackendResources(data);
        }
      })
      .catch(() => {});
    return () => {
      active = false;
    };
  }, []);

  // Listen for Escape key to clear search
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') {
        setSearchQuery('');
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const principles = [
    {
      num: '01',
      title: 'Pause the Pressure',
      subtitle: 'The Golden Protective Habit',
      icon: 'hourglass_top',
      keywords: 'pressure urgency hurry emergency deadline arrest 1 hour calm golden rule',
      why: 'Scammers manufacture fake deadlines ("within 1 hour", "immediate arrest pending") specifically to bypass your rational, critical brain and trigger fear.',
      move: 'Breathe deeply. Step back. Any authentic institutional emergency can comfortably wait 10 minutes while you calmly cross-verify.',
      rule: 'Zero Urgency Rule',
      ruleIcon: 'verified',
      isPrimary: true,
    },
    {
      num: '02',
      title: 'Never Share OTPs or Passwords',
      subtitle: 'The Sacred Key Boundary',
      icon: 'key',
      keywords: 'otp password 2fa two-factor code authentication bank verification sms credentials',
      why: 'One-Time Passwords (OTPs) and 2-factor codes are designed strictly for user-to-system entry. Scammers pose as tech support to trick you into whispering their entry pass.',
      move: 'No legitimate bank, agency, or tech company will EVER request you to read back an SMS verification code over the telephone or chat. Treat codes like confidential PINs.',
      rule: 'Strict Zero-Share',
      ruleIcon: 'lock',
    },
    {
      num: '03',
      title: 'Verify Independently',
      subtitle: 'Bypass Caller ID Illusions',
      icon: 'call_end',
      keywords: 'verify independently caller id spoofing official website back of card phone number hang up',
      why: 'VoIP technology allows attackers to easily falsify (spoof) caller ID names, displaying your bank’s actual name or the local police precinct number effortlessly.',
      move: 'Politely hang up. Flip your credit card over and dial the phone number printed on the plastic, or locate the official statement URL on a separate browser.',
      rule: 'Out-of-Band Check',
      ruleIcon: 'cached',
    },
    {
      num: '04',
      title: 'Beware Untrusted Links',
      subtitle: 'Look at the True Domain',
      icon: 'link_off',
      keywords: 'links urls typos text sms delivery parcel tracking postal usps fedex dhl clicks',
      why: 'Deceptive SMS notifications ("USPS: $0.35 redelivery fee required") route users to credential-harvesting lookalikes that imitate real portals down to the pixel.',
      move: 'Never tap links in unexpected text messages. Open your browser independently and search for the service, or launch the genuine native smartphone application.',
      rule: 'Direct Address Entry',
      ruleIcon: 'open_in_browser',
    },
    {
      num: '05',
      title: 'The Family Emergency Rule',
      subtitle: 'Defeat AI Voice Cloning',
      icon: 'record_voice_over',
      keywords: 'family emergency ai voice audio cloning deepfake grandchild grandparent bail jail hospital secret code word',
      why: 'Modern AI voice synthesizers require only 3 seconds of audio harvested from social videos to mimic a child or grandchild sobbing about an urgent car crash or arrest.',
      move: 'Agree on an unwritten, secret "Family Safe Word" today. If a distress call arrives, calmly ask: "What is our family word?" Then hang up and call their standard cell.',
      rule: 'Family Challenge Phrase',
      ruleIcon: 'family_restroom',
    },
    {
      num: '06',
      title: 'Gift Cards & Crypto = Fraud',
      subtitle: '100% Definitive Red Flag',
      icon: 'credit_card_off',
      keywords: 'gift cards crypto cryptocurrency bitcoin apple target zelle payment wire irs fines fraud',
      why: 'Unlike bank transfers which carry federal clawback and fraud protections, gift cards and cryptocurrency ATMs are instantaneous, non-refundable, and completely untraceable.',
      move: 'Remember this absolute fact: No federal agency (IRS, FBI, SSA), local police department, or utility company will ever mandate payment via Apple Gift Cards or Bitcoin kiosks.',
      rule: 'Zero Legit Exceptions',
      ruleIcon: 'gavel',
      isAlert: true,
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
      p.move.toLowerCase().includes(q) ||
      p.rule.toLowerCase().includes(q)
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
    if (navigator.clipboard) {
      navigator.clipboard.writeText(window.location.href);
      setCopiedLink(true);
      setTimeout(() => setCopiedLink(false), 2000);
    }
  };

  return (
    <div className="ambient-glow-container">
      {/* Subtle Ambient Glow Blobs */}
      <div className="ambient-glow-1" aria-hidden="true" />
      <div className="ambient-glow-2" aria-hidden="true" />

      <div className="page-container">
        {/* Editorial Header Section */}
        <div className="page-hero">
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '10px' }}>
            <span className="hero-overline" style={{ margin: 0 }}>
              <span className="material-symbols-outlined text-[15px]">verified_user</span>
              EMPOWERMENT &amp; HUMAN RESILIENCE
            </span>
            <span style={{ color: 'var(--ink-secondary)', fontSize: '0.82rem', fontWeight: 600 }}>
              • Edition 2025
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-end', flexWrap: 'wrap', gap: '20px' }}>
            <div style={{ maxWidth: '680px' }}>
              <h1 className="page-title">ScamShield Safety Guide</h1>
              <p className="page-subtitle">
                Simple rules, clear instincts. How to recognize psychological traps and respond with quiet, unshakeable confidence.
              </p>
            </div>

            {/* Defensive Status Badge */}
            <div style={{
              background: 'var(--surface-low)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-lg)',
              padding: '12px 18px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              boxShadow: 'var(--shadow-sm)'
            }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: 'var(--radius-md)',
                background: 'var(--teal-secondary)',
                color: '#ffffff',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}>
                <span className="material-symbols-outlined text-[22px]">psychology</span>
              </div>
              <div>
                <div style={{ fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--teal-secondary)' }}>
                  Mental Firewall
                </div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.05rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
                  6 Principles Active
                </div>
              </div>
            </div>
          </div>

          {/* Search Bar */}
          <div style={{ marginTop: '24px' }}>
            <div className="guide-search-box">
              <span className="material-symbols-outlined text-[22px]" style={{ color: 'var(--ink-muted)', marginRight: '8px' }}>
                search
              </span>
              <input
                id="guide-search"
                type="text"
                className="guide-search-input"
                placeholder="Search scam tactics (e.g. delivery fee, IRS, romance, fake job, bank alert)..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                aria-label="Search scam tactics"
              />
              <kbd className="kbd-shortcut">ESC to clear</kbd>
              {searchQuery && (
                <button
                  type="button"
                  className="guide-search-clear-btn"
                  onClick={() => setSearchQuery('')}
                  title="Clear filter"
                  aria-label="Clear filter"
                >
                  <span className="material-symbols-outlined text-[18px]">close</span>
                </button>
              )}
            </div>

            {/* Quick Filters Chips */}
            <div className="guide-quick-jump">
              <span className="quick-jump-label">QUICK JUMP:</span>
              {[
                { label: 'Urgency Trap', query: 'pressure' },
                { label: '2FA & SMS codes', query: 'otp' },
                { label: 'AI Audio Cloning', query: 'voice' },
                { label: 'Gift Cards / Crypto', query: 'crypto' },
                { label: 'Incident Response', query: 'recovery' },
              ].map((item) => (
                <button
                  key={item.label}
                  type="button"
                  className={`quick-jump-chip ${searchQuery.toLowerCase() === item.query ? 'active' : ''}`}
                  onClick={() => setSearchQuery(searchQuery === item.query ? '' : item.query)}
                >
                  {item.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Warm Editorial Quote Banner */}
        <section className="editorial-quote-banner" aria-label="Defensive Reality">
          <div className="quote-left">
            <div className="subcard-tag move">
              <span className="material-symbols-outlined text-[16px]">lightbulb</span>
              The Human-First Defense Reality
            </div>
            <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: 700, color: 'var(--forest-primary)', lineHeight: 1.4 }}>
              "Scams do not prey on lack of intelligence; they exploit natural empathy, civic compliance, and artificial urgency."
            </p>
            <p style={{ fontSize: '0.86rem', color: 'var(--ink-secondary)', marginTop: '6px' }}>
              Understanding the psychological lever is your strongest cryptographic key.
            </p>
          </div>

          <div className="quote-right">
            <div className="golden-pause-card">
              <div className="golden-pause-icon-box">
                <span className="material-symbols-outlined text-[26px]">timer</span>
              </div>
              <div>
                <p style={{ fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--ink-muted)' }}>
                  GOLDEN PAUSE
                </p>
                <p style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: 800, color: 'var(--forest-primary)' }}>
                  10 Minutes
                </p>
                <p style={{ fontSize: '0.76rem', color: 'var(--teal-secondary)', fontWeight: 600 }}>
                  Neutralizes High-Pressure Tactics
                </p>
              </div>
            </div>
          </div>
        </section>

        {/* Core Principles Bento Grid */}
        <section style={{ marginBottom: '48px' }} aria-label="Core Defense Principles">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--teal-secondary)' }}>
                FOUNDATIONAL IMMUNITY
              </span>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', fontWeight: 800, color: 'var(--forest-primary)' }}>
                Core Defense Principles
              </h2>
            </div>
            <span style={{ fontSize: '0.82rem', color: 'var(--ink-secondary)' }}>
              {filteredPrinciples.length} of 6 tactical playbooks
            </span>
          </div>

          <div className="principles-grid">
            {filteredPrinciples.map((p) => (
              <article key={p.num} className="principle-card">
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                    <div className={`principle-icon-box ${p.isAlert ? 'alert' : ''}`}>
                      <span className="material-symbols-outlined text-[26px]">{p.icon}</span>
                    </div>
                    <span className={`principle-badge ${p.isPrimary ? 'primary' : p.isAlert ? 'alert' : ''}`}>
                      Principle {p.num}
                    </span>
                  </div>

                  <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', fontWeight: 700, color: 'var(--forest-primary)', marginBottom: '4px' }}>
                    {p.title}
                  </h3>
                  <div style={{ fontSize: '0.82rem', color: p.isAlert ? 'var(--risk-high-ink)' : 'var(--teal-secondary)', fontWeight: 600, marginBottom: '14px' }}>
                    {p.subtitle}
                  </div>

                  {/* WHY IT WORKS */}
                  <div className="principle-subcard-why">
                    <div className="subcard-tag why">
                      <span className="material-symbols-outlined text-[15px]">psychology_alt</span>
                      WHY IT WORKS
                    </div>
                    <p style={{ fontSize: '0.82rem', color: 'var(--ink-secondary)', lineHeight: 1.5 }}>
                      {p.why}
                    </p>
                  </div>

                  {/* YOUR MOVE */}
                  <div className="principle-subcard-move">
                    <div className="subcard-tag move">
                      <span className="material-symbols-outlined text-[15px]">shield</span>
                      YOUR MOVE
                    </div>
                    <p style={{ fontSize: '0.82rem', color: 'var(--forest-primary)', fontWeight: 500, lineHeight: 1.5 }}>
                      {p.move}
                    </p>
                  </div>
                </div>

                {/* Footer rule */}
                <div className="principle-footer-rule">
                  <span style={{ display: 'flex', alignItems: 'center', gap: '6px', fontWeight: 600 }}>
                    <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: p.isAlert ? 'var(--risk-high-ink)' : 'var(--teal-secondary)' }} />
                    {p.rule}
                  </span>
                  <span className="material-symbols-outlined text-[18px]" style={{ color: p.isAlert ? 'var(--risk-high-ink)' : 'var(--teal-secondary)' }}>
                    {p.ruleIcon}
                  </span>
                </div>
              </article>
            ))}
          </div>
        </section>

        {/* Interactive Incident Response Checklist */}
        <section className="recovery-sequence-wrapper" aria-label="Immediate Incident Recovery">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '20px', marginBottom: '24px' }}>
            <div style={{ maxWidth: '640px' }}>
              <div style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                padding: '4px 12px',
                borderRadius: 'var(--radius-full)',
                background: 'var(--risk-high-bg)',
                color: 'var(--risk-high-ink)',
                fontSize: '0.72rem',
                fontWeight: 700,
                letterSpacing: '0.04em',
                marginBottom: '8px'
              }}>
                <span className="material-symbols-outlined text-[15px]">emergency_home</span>
                IMMEDIATE RECOVERY SEQUENCE
              </div>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', fontWeight: 800, color: 'var(--forest-primary)' }}>
                What to do if you suspect you already responded
              </h2>
              <p style={{ fontSize: '0.9rem', color: 'var(--ink-secondary)', marginTop: '4px' }}>
                No shame, no hesitation. Taking calm action within minutes cuts attacker access completely.
              </p>
            </div>

            {/* SVG Progress Ring */}
            <div className="checklist-progress-ring-box">
              <div style={{ position: 'relative', width: '48px', height: '48px', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                <svg viewBox="0 0 36 36" style={{ width: '48px', height: '48px', transform: 'rotate(-90deg)' }}>
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="#e3e3de"
                    strokeWidth="3.2"
                  />
                  <path
                    d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                    fill="none"
                    stroke="var(--teal-secondary)"
                    strokeWidth="3.2"
                    strokeDasharray={`${progressPercent}, 100`}
                    strokeLinecap="round"
                    style={{ transition: 'stroke-dasharray 0.3s ease' }}
                  />
                </svg>
                <span style={{ position: 'absolute', fontSize: '0.74rem', fontWeight: 800, color: 'var(--forest-primary)' }}>
                  {completedSteps}/5
                </span>
              </div>
              <div>
                <p style={{ fontSize: '0.68rem', fontWeight: 700, letterSpacing: '0.05em', textTransform: 'uppercase', color: 'var(--ink-muted)' }}>
                  CHECKLIST STATUS
                </p>
                <p style={{ fontSize: '0.9rem', fontWeight: 700, color: completedSteps === 5 ? 'var(--teal-secondary)' : 'var(--forest-primary)' }}>
                  {completedSteps === 0 ? 'Triage Ready' : completedSteps === 5 ? 'Fully Protected' : `${progressPercent}% Secured`}
                </p>
              </div>
            </div>
          </div>

          {/* 5 Practical Steps */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {[
              {
                time: 'T + 0 Minutes',
                title: 'Step 1: Sever Communication Instantly',
                desc: 'Hang up immediately. Block the phone number. Close chat sessions. If they instructed you to install remote software (e.g., AnyDesk, TeamViewer), disconnect your Wi-Fi or turn off your device.',
              },
              {
                time: 'T + 2 Minutes',
                title: 'Step 2: Lock Compromised Cards via App',
                desc: 'Open your verified banking app and toggle the "Lock / Freeze Card" switch for any debit or credit accounts mentioned. This prevents pending authorizations immediately.',
              },
              {
                time: 'T + 5 Minutes',
                title: 'Step 3: Update Core Passwords from a Clean Device',
                desc: 'Using a separate phone or family computer, change the master password for your primary email and bank portal. Sign out of all active remote web sessions.',
              },
              {
                time: 'T + 30 Minutes',
                title: 'Step 4: File Reports with Official Regulatory Agencies',
                desc: 'Submit fraud details directly to IdentityTheft.gov and ReportFraud.ftc.gov. These reports establish an official legal affidavit used to contest fraudulent debt.',
              },
              {
                time: 'Essential Care',
                title: 'Step 5: Talk with Someone You Trust',
                desc: 'Social isolation helps scammers. Call a trusted child, sibling, friend, or advocate. Sharing what took place reduces stress and breaks the psychological hold.',
              },
            ].map((step, idx) => (
              <label
                key={idx}
                className={`checklist-step-item ${checkedSteps[idx] ? 'checked' : ''}`}
              >
                <input
                  type="checkbox"
                  checked={checkedSteps[idx]}
                  onChange={() => toggleStep(idx)}
                  style={{
                    width: '18px',
                    height: '18px',
                    marginTop: '3px',
                    accentColor: 'var(--forest-primary)',
                    cursor: 'pointer',
                  }}
                />
                <div style={{ flex: 1 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '6px' }}>
                    <span style={{ fontSize: '0.96rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
                      {step.title}
                    </span>
                    <span className="step-time-pill">{step.time}</span>
                  </div>
                  <p style={{ fontSize: '0.85rem', color: 'var(--ink-secondary)', marginTop: '4px', lineHeight: 1.5 }}>
                    {step.desc}
                  </p>
                </div>
              </label>
            ))}
          </div>
        </section>

        {/* Verified Contact Directory */}
        <section style={{ marginBottom: '48px' }} aria-label="Official Emergency Directory">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px', marginBottom: '8px' }}>
            <div>
              <span style={{ fontSize: '0.72rem', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--teal-secondary)' }}>
                OFFICIAL DIRECTORY
              </span>
              <h2 style={{ fontFamily: 'var(--font-display)', fontSize: '1.6rem', fontWeight: 800, color: 'var(--forest-primary)' }}>
                Emergency Verified Contacts
              </h2>
            </div>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: '4px 12px',
              borderRadius: 'var(--radius-full)',
              background: 'var(--surface-mint)',
              color: 'var(--teal-secondary)',
              fontSize: '0.78rem',
              fontWeight: 600,
            }}>
              <span className="material-symbols-outlined text-[16px]">verified</span>
              Vetted &amp; Direct Numbers
            </span>
          </div>
          <p style={{ fontSize: '0.88rem', color: 'var(--ink-secondary)', marginBottom: '24px' }}>
            Do not rely on web search advertisements for phone numbers. Use these verified consumer lines directly.
          </p>

          <div className="contacts-directory-grid">
            {/* Major Banking Institutions Fraud Hub */}
            <div className="directory-hub-card">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
                  <div style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--surface-high)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--forest-primary)',
                  }}>
                    <span className="material-symbols-outlined text-[24px]">account_balance</span>
                  </div>
                  <div>
                    <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.15rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
                      Tier-1 Banking Fraud Desks
                    </h3>
                    <p style={{ fontSize: '0.76rem', color: 'var(--ink-muted)' }}>Available 24 hours / 7 days</p>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  {[
                    { bank: 'JPMorgan Chase', dept: 'Card & Account Fraud Department', phone: '1-800-935-9935', tel: '18009359935' },
                    { bank: 'Bank of America', dept: 'Fraud Prevention & Claims', phone: '1-800-432-1000', tel: '18004321000' },
                    { bank: 'Wells Fargo', dept: 'Identity Fraud Escalation', phone: '1-800-869-3557', tel: '18008693557' },
                    { bank: 'Citibank', dept: 'Security & Suspicious Transfers', phone: '1-800-950-5114', tel: '18009505114' },
                  ].map((b) => (
                    <div key={b.bank} className="directory-item-row">
                      <div>
                        <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--ink-primary)' }}>{b.bank}</div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--ink-secondary)' }}>{b.dept}</div>
                      </div>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.84rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
                          {b.phone}
                        </span>
                        <a
                          href={`tel:${b.tel}`}
                          className="directory-call-btn"
                          title={`Call ${b.bank} fraud department`}
                          aria-label={`Call ${b.bank} fraud department`}
                        >
                          <span className="material-symbols-outlined text-[18px]">call</span>
                        </a>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div style={{ marginTop: '16px', padding: '10px 14px', background: 'var(--surface-low)', borderRadius: 'var(--radius-md)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '0.78rem' }}>
                <span style={{ color: 'var(--ink-secondary)' }}>Using a regional credit union?</span>
                <span style={{ color: 'var(--teal-secondary)', fontWeight: 600 }}>Inspect back of your plastic debit card</span>
              </div>
            </div>

            {/* Official Federal Regulatory & Advocacy Agencies */}
            <div className="directory-hub-card">
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '20px' }}>
                  <div style={{
                    width: '42px',
                    height: '42px',
                    borderRadius: 'var(--radius-md)',
                    background: 'var(--surface-mint)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    color: 'var(--teal-secondary)',
                  }}>
                    <span className="material-symbols-outlined text-[24px]">policy</span>
                  </div>
                  <div>
                    <h3 style={{ fontFamily: 'var(--font-display)', fontSize: '1.15rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
                      Official Reporting Agencies
                    </h3>
                    <p style={{ fontSize: '0.76rem', color: 'var(--ink-muted)' }}>Federal consumer protection &amp; advocacy</p>
                  </div>
                </div>

                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div className="directory-item-row">
                    <div>
                      <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--ink-primary)' }}>Federal Trade Commission (FTC)</div>
                      <div style={{ fontSize: '0.76rem', color: 'var(--ink-secondary)' }}>Civil fraud reporting and remediation</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.84rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
                        1-877-FTC-HELP
                      </span>
                      <a
                        href="tel:18773824357"
                        className="directory-call-btn"
                        title="Call FTC hotline"
                        aria-label="Call FTC hotline"
                      >
                        <span className="material-symbols-outlined text-[18px]">call</span>
                      </a>
                    </div>
                  </div>

                  <div className="directory-item-row">
                    <div>
                      <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--ink-primary)' }}>FBI Internet Crime Complaint Center (IC3)</div>
                      <div style={{ fontSize: '0.76rem', color: 'var(--ink-secondary)' }}>Wire fraud, ransomware &amp; cybercrime</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.84rem', fontWeight: 700, color: 'var(--teal-secondary)' }}>
                        ic3.gov
                      </span>
                      <a
                        href="https://www.ic3.gov"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="directory-call-btn"
                        title="Open IC3 portal"
                        aria-label="Open IC3 portal"
                      >
                        <span className="material-symbols-outlined text-[18px]">open_in_new</span>
                      </a>
                    </div>
                  </div>

                  <div className="directory-item-row">
                    <div>
                      <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--ink-primary)' }}>AARP Fraud Watch Network</div>
                      <div style={{ fontSize: '0.76rem', color: 'var(--ink-secondary)' }}>Free helpline for seniors and families</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.84rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
                        1-877-908-3360
                      </span>
                      <a
                        href="tel:18779083360"
                        className="directory-call-btn"
                        title="Call AARP Fraud Helpline"
                        aria-label="Call AARP Fraud Helpline"
                      >
                        <span className="material-symbols-outlined text-[18px]">call</span>
                      </a>
                    </div>
                  </div>

                  <div className="directory-item-row">
                    <div>
                      <div style={{ fontSize: '0.88rem', fontWeight: 700, color: 'var(--ink-primary)' }}>National Cyber Crime Portal (India)</div>
                      <div style={{ fontSize: '0.76rem', color: 'var(--ink-secondary)' }}>Financial fraud reporting helpline: 1930</div>
                    </div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                      <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.84rem', fontWeight: 700, color: 'var(--forest-primary)' }}>
                        cybercrime.gov.in
                      </span>
                      <a
                        href="https://cybercrime.gov.in"
                        target="_blank"
                        rel="noopener noreferrer"
                        className="directory-call-btn"
                        title="Open National Cyber Crime Reporting Portal"
                        aria-label="Open National Cyber Crime Reporting Portal"
                      >
                        <span className="material-symbols-outlined text-[18px]">open_in_new</span>
                      </a>
                    </div>
                  </div>
                </div>
              </div>

              {/* Dynamic resources from ScamShield API */}
              {backendResources.reporting_resources && Object.keys(backendResources.reporting_resources).length > 0 && (
                <div style={{ marginTop: '16px', paddingTop: '12px', borderTop: '1px solid var(--border-subtle)', display: 'flex', flexWrap: 'wrap', gap: '8px' }}>
                  {Object.entries(backendResources.reporting_resources).map(([name, url]) => (
                    <a
                      key={name}
                      href={url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="copy-pill-btn"
                      title={`Open official portal: ${name}`}
                    >
                      <span className="material-symbols-outlined text-[14px]">open_in_new</span>
                      <span>{name}</span>
                    </a>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>

        {/* PRINT & SHARE ACTION FOOTER */}
        <section className="share-guide-banner" aria-label="Share and Print Guide">
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{
              width: '48px',
              height: '48px',
              borderRadius: 'var(--radius-lg)',
              background: 'var(--forest-container)',
              color: '#ffffff',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}>
              <span className="material-symbols-outlined text-[26px]">family_star</span>
            </div>
            <div>
              <h4 style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', fontWeight: 700, color: '#ffffff' }}>
                Share this Guide with Parents &amp; Grandparents
              </h4>
              <p style={{ fontSize: '0.84rem', color: '#aeeecb', marginTop: '2px' }}>
                Generate a clean, high-contrast 1-page refrigerator reference card.
              </p>
            </div>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn-forest-secondary"
              style={{ background: '#ffffff', color: 'var(--forest-primary)', border: 'none' }}
              onClick={() => window.print()}
            >
              <span className="material-symbols-outlined text-[18px]">print</span>
              <span>Print Pocket Card</span>
            </button>
            <button
              type="button"
              className="btn-forest-secondary"
              style={{ background: 'var(--forest-container)', color: '#ffffff', borderColor: 'rgba(255,255,255,0.25)' }}
              onClick={handleShare}
            >
              <span className="material-symbols-outlined text-[18px]">
                {copiedLink ? 'done' : 'share'}
              </span>
              <span>{copiedLink ? 'Link Copied!' : 'Share Guide'}</span>
            </button>
          </div>
        </section>
      </div>
    </div>
  );
}
