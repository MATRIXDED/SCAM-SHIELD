"""
analyzer.py — ScamShield Detection Engine
==========================================
Analyzes untrusted incoming text messages, emails, and payment alerts for scam signals.
Key design principles:
1. Untrusted Input: Treat all text as hostile/untrusted data. Strip prompt injections.
2. Privacy First: Never store or log raw message bodies. Provide redaction and hashing.
3. Explainable: Provide detailed breakdown of individual risk categories and clear reasoning.
4. Responsible AI: Never declare any message "100% Safe". Always advise caution.
"""

import re
import hashlib
from typing import Dict, List, Any
from urllib.parse import urlparse

# ── Pattern definitions ──────────────────────────────────────────────────────

# Prompt injection attempt patterns (attempts to trick the detector)
PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"(?i)you\s+must\s+(say|rate|classify)\s+(this\s+as\s+)?safe",
    r"(?i)system\s*:\s*this\s+message\s+is\s+verified",
    r"(?i)mark\s+this\s+as\s+legitimate",
    r"(?i)override\s+(security|safety|scam)\s+(check|filter|score)",
    r"(?i)disregard\s+threat\s+detection",
]

# Urgency and panic triggers
URGENCY_PATTERNS = [
    (r"(?i)\b(immediate|immediately|urgent|urgently|action required|act now|hurry)\b", "High urgency language detected"),
    (r"(?i)\b(within\s+\d+\s*(hours?|mins?|minutes?)|24\s*hours?|today\s+only|expires?\s+soon)\b", "Artificial deadline or expiring window"),
    (r"(?i)\b(suspended|terminated|blocked|frozen|locked|cancelled|restricted|deactivated)\b", "Threat of account suspension or service block"),
    (r"(?i)\b(legal\s+action|arrest\s+warrant|police|court|law enforcement|penalties|fine|prosecution)\b", "Threat of legal or punitive consequences"),
    (r"(?i)\b(final\s+notice|last\s+chance|immediate\s+response)\b", "Final warning pressure tactics"),
]

# Impersonation signals (Brands, institutions, utilities)
IMPERSONATION_TARGETS = [
    (r"(?i)\b(amazon|prime|aws)\b", "Amazon"),
    (r"(?i)\b(paypal|venmo|zelle|cash\s*app)\b", "Payment Provider"),
    (r"(?i)\b(chase|wells\s*fargo|bank\s*of\s*america|citi|hsbc|barclays|td\s*bank)\b", "Major Banking Institution"),
    (r"(?i)\b(fedex|ups|usps|dhl|royal\s*mail|courier|customs|delivery\s+agent)\b", "Postal / Courier Delivery Service"),
    (r"(?i)\b(apple|icloud|google|microsoft|geek\s*squad|mcafee|norton)\b", "Tech / Software Support"),
    (r"(?i)\b(irs|hmrc|tax\s*department|social\s*security|ssa|govt|government)\b", "Government / Tax Authority"),
    (r"(?i)\b(netflix|spotify|att|verizon|t-mobile)\b", "Telecom / Subscription Service"),
]

# OTP / Credential Harvesting
OTP_PATTERNS = [
    (r"(?i)\b(otp|one[- ]time\s+password|verification\s+code|security\s+code|2fa|pin|passcode)\b", "Mentions verification code / OTP"),
    (r"(?i)\b(do\s*not\s*share|share\s+this\s+code|reply\s+with\s+(the\s+)?code|forward\s+this\s+code|send\s+code)\b", "Requests disclosure of secret code"),
    (r"(?i)\b(enter\s+your\s+password|confirm\s+your\s+pin|login\s+to\s+verify|update\s+credentials)\b", "Credential submission request"),
]

# Payment Pressure & Financial Demands
PAYMENT_PATTERNS = [
    (r"(?i)\b(gift\s*card|itunes|steam\s*card|google\s*play\s*card|vanilla\s*visa)\b", "High risk: Gift card payment requested"),
    (r"(?i)\b(bitcoin|crypto|usdt|eth|btc|wallet\s+address)\b", "High risk: Cryptocurrency payment requested"),
    (r"(?i)\b(wire\s+transfer|western\s*union|moneygram)\b", "Untraceable wire transfer requested"),
    (r"(?i)\b(unpaid\s+invoice|pending\s+bill|overdue\s+payment|debt\s+collection)\b", "Unsolicited invoice or debt collection claim"),
    (r"(?i)\b(refund\s+processing|fee\s+required|clearance\s+fee|processing\s+fee)\b", "Upfront fee requested to release funds"),
]

# Prize, Lottery, Refund, and Delivery Lures
LURE_PATTERNS = [
    (r"(?i)\b(won|winner|lottery|sweepstakes|jackpot|selected\s+to\s+receive|claim\s+your\s+prize)\b", "Prize or sweepstakes lure"),
    (r"(?i)\b(refund\s+of\s+\$?\d+|overpaid|accidental\s+charge|reimbursement)\b", "Unsolicited refund or overpayment lure"),
    (r"(?i)\b(unclaimed\s+package|package\s+pending|delivery\s+failed|customs\s+fee\s+due)\b", "Fake delivery package lure"),
    (r"(?i)\b(inheritance|beneficiary|foreign\s+funds|next\s+of\s+kin)\b", "Inheritance / Nigerian prince style lure"),
]

# Suspicious Link Indicators
SUSPICIOUS_TLDS = {".xyz", ".top", ".buzz", ".club", ".tk", ".ml", ".ga", ".cf", ".gq", ".work", ".click", ".link"}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "is.gd", "buff.ly", "ow.ly", "cutt.ly", "rb.gy"}

URL_REGEX = re.compile(
    r"(?i)\b(?:https?://|www\d{0,3}\.|\b[a-z0-9.-]+\.[a-z]{2,10}(?:/[^\s]*)?)",
    re.IGNORECASE
)


def extract_links(text: str) -> List[Dict[str, Any]]:
    """Extract and analyze URLs found within the text."""
    raw_urls = URL_REGEX.findall(text)
    links_data = []

    for raw in raw_urls:
        candidate = raw.strip(".,;:()[]{}'\"")
        parse_target = candidate if candidate.startswith(("http://", "https://")) else "http://" + candidate
        try:
            parsed = urlparse(parse_target)
            domain = (parsed.netloc or parsed.path.split("/")[0]).lower()
            
            if "." not in domain or len(domain.split(".")[-1]) < 2:
                continue

            flags = []
            is_suspicious = False
            
            # Check URL shortener
            if any(domain == s or domain.endswith("." + s) for s in SHORTENERS):
                flags.append("Obfuscated link (URL shortener hides true destination)")
                is_suspicious = True

            # Check suspicious TLD
            for tld in SUSPICIOUS_TLDS:
                if domain.endswith(tld):
                    flags.append(f"Suspicious top-level domain ({tld})")
                    is_suspicious = True
                    break

            # Check IP address as host
            if re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", domain):
                flags.append("Direct IP address used instead of reputable domain name")
                is_suspicious = True

            # Check deceptive brand substring in subdomain
            for brand in ["amazon", "paypal", "apple", "chase", "netflix", "usps", "fedex", "google"]:
                if brand in domain:
                    legit_suffixes = (f"{brand}.com", f"{brand}.org", f"{brand}.co.uk", f"{brand}.ca", f"{brand}.in")
                    if not any(domain == s or domain.endswith("." + s) for s in legit_suffixes):
                        flags.append(f"Lookalike brand spoofing ({brand} found in suspicious domain: {domain})")
                        is_suspicious = True

            # Check for HTTP (not HTTPS)
            if raw.startswith("http://"):
                flags.append("Insecure plain HTTP link (no TLS encryption)")

            links_data.append({
                "url": candidate,
                "domain": domain,
                "is_suspicious": is_suspicious,
                "flags": flags,
            })
        except Exception:
            continue

    return links_data


def detect_prompt_injection(text: str) -> bool:
    """Detect if the input text contains attempts to hijack or manipulate evaluation."""
    for pattern in PROMPT_INJECTION_PATTERNS:
        if re.search(pattern, text):
            return True
    return False


def hash_content(text: str) -> str:
    """Return a SHA-256 fingerprint of the text so raw user text is never logged."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def generate_suggested_response(impersonated: List[str], risk_level: str) -> str:
    """Generate a safe, protective response or action note that the user can copy."""
    target = impersonated[0] if impersonated else "the sender"
    if risk_level == "HIGH RISK":
        return (
            f"Do not reply to this message. If you suspect an issue with your {target} account, "
            f"navigate independently to their official verified website or call the customer service "
            f"phone number printed on the back of your official statement/card."
        )
    elif risk_level == "ELEVATED RISK":
        return (
            f"I have received this notification regarding {target}. I will not click any links or share codes. "
            f"I am verifying this through official channels directly."
        )
    else:
        return (
            "No immediate high-risk scam indicators found, but stay vigilant: never share OTPs, passwords, "
            "or send payments based on unverified text/email messages."
        )


def analyze_message(text: str, metadata: Dict[str, Any] = None) -> Dict[str, Any]:
    """
    Primary analysis entry point.
    Returns structured, explainable assessment with breakdown.
    Never declares a message 100% safe.
    """
    if metadata is None:
        metadata = {}

    stripped = text.strip() if text else ""
    if not stripped:
        return {
            "error": "Empty message provided. Please paste the suspicious message text.",
            "status": "error"
        }

    # 1. Prompt Injection Defense
    injection_attempt = detect_prompt_injection(stripped)

    # 2. Extract Categories
    signals: Dict[str, List[str]] = {
        "urgency": [],
        "impersonation": [],
        "suspicious_links": [],
        "otp_requests": [],
        "payment_pressure": [],
        "lures": [],
    }

    warning_signs: List[str] = []
    points = 0

    # Test Urgency
    for pattern, desc in URGENCY_PATTERNS:
        if re.search(pattern, stripped):
            signals["urgency"].append(desc)
            if desc not in warning_signs:
                warning_signs.append(desc)
            points += 20

    # Test Impersonation
    impersonated_entities = []
    for pattern, entity_name in IMPERSONATION_TARGETS:
        if re.search(pattern, stripped):
            note = f"Suspected impersonation of {entity_name}"
            signals["impersonation"].append(note)
            impersonated_entities.append(entity_name)
            if note not in warning_signs:
                warning_signs.append(note)
            points += 20

    # Test OTP / Verification Codes (Critical acute threat)
    for pattern, desc in OTP_PATTERNS:
        if re.search(pattern, stripped):
            signals["otp_requests"].append(desc)
            if desc not in warning_signs:
                warning_signs.append(desc)
            points += 35

    # Test Payment Pressure
    for pattern, desc in PAYMENT_PATTERNS:
        if re.search(pattern, stripped):
            signals["payment_pressure"].append(desc)
            if desc not in warning_signs:
                warning_signs.append(desc)
            points += 30

    # Test Lures
    for pattern, desc in LURE_PATTERNS:
        if re.search(pattern, stripped):
            signals["lures"].append(desc)
            if desc not in warning_signs:
                warning_signs.append(desc)
            points += 25

    # Test Links
    extracted_links = extract_links(stripped)
    for link in extracted_links:
        for f in link["flags"]:
            signals["suspicious_links"].append(f"{link['url']}: {f}")
            if f not in warning_signs:
                warning_signs.append(f)
            points += 25

    # Add points if injection attempt was detected
    if injection_attempt:
        warning_signs.insert(0, "Prompt injection attempt detected inside message payload")
        points += 35

    # Escalation: Unsolicited OTP combined with urgency or brand impersonation is an immediate high-risk takeover attempt
    if signals["otp_requests"] and (signals["impersonation"] or signals["urgency"] or signals["payment_pressure"]):
        points = max(points, 75)

    # Cap score at 98 (never 100% scam, never 0% definitely safe)
    # Minimum score is 5 to reflect foundational caution
    raw_score = max(5, min(98, points))

    # Risk level classification
    if raw_score >= 60:
        risk_level = "HIGH RISK"
        risk_color = "#ef4444"  # Red
        summary_statement = "Severe scam indicators detected. Strong likelihood of fraudulent solicitation."
    elif raw_score >= 30:
        risk_level = "ELEVATED RISK"
        risk_color = "#f59e0b"  # Amber
        summary_statement = "Suspicious elements identified. Exercise high caution and do not click links."
    else:
        risk_level = "LOW RISK (Caution Still Advised)"
        risk_color = "#10b981"  # Emerald
        summary_statement = "No obvious scam signals matched, but caution is always advised. Legitimate companies will never request your OTP or password."

    # Next steps recommendations
    safe_next_steps = [
        "Do NOT click any links, download attachments, or call numbers provided inside the message.",
        "Never share One-Time Passwords (OTP), 2FA codes, PINs, or banking passwords with anyone.",
        "If the message claims to be from a company (e.g. Amazon, your bank), open your browser independently and log into your official account directly.",
        "Report and block the sender in your SMS or email app.",
    ]
    if signals["payment_pressure"]:
        safe_next_steps.insert(0, "Legitimate organizations NEVER demand payment via gift cards, cryptocurrency, or peer-to-peer apps.")
    if signals["otp_requests"]:
        safe_next_steps.insert(0, "IMMEDIATE WARNING: Real customer service will NEVER ask you to read out or forward an OTP or verification code.")

    suggested_response = generate_suggested_response(impersonated_entities, risk_level)

    # Privacy preservation: We generate a safe fingerprint and snippet length
    content_hash = hash_content(stripped)

    return {
        "status": "success",
        "fingerprint": content_hash,
        "preview_length": len(stripped),
        "risk_score": raw_score,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "summary": summary_statement,
        "warning_signs": warning_signs,
        "breakdown": {
            "urgency": signals["urgency"],
            "impersonation": signals["impersonation"],
            "suspicious_links": signals["suspicious_links"],
            "otp_requests": signals["otp_requests"],
            "payment_pressure": signals["payment_pressure"],
            "lures": signals["lures"],
        },
        "safe_next_steps": safe_next_steps,
        "suggested_response": suggested_response,
        "disclaimer": "ScamShield provides heuristic risk evaluation. No system can guarantee a message is definitely safe. When in doubt, verify independently through official channels.",
        "prompt_injection_detected": injection_attempt,
        "links_found": len(extracted_links),
    }
