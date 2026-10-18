"""
analyzer.py — ScamShield Detection Engine (Hardened v2)
=========================================================
Analyzes untrusted incoming text messages, emails, and payment alerts for scam signals.

Key design principles:
1. Untrusted Input: Treat all text as hostile/untrusted data. Strip prompt injections.
2. Normalization without Bias: Unicode NFKC and homoglyph resolution to catch hidden signals.
   Original text is preserved for user display; normalization is NOT proof of fraud.
3. High Specificity: Disentangle legitimate notifications (e.g. OTP delivery with warning not to share)
   from active harvesting attacks. Contextualize isolated keywords (police, fine, winner, Prime, PIN).
4. Regional Threat Awareness: Heuristics for UPI collect fraud, KYC cancellation threats,
   fake "digital arrest" extortion, and remote-access APK/screen-sharing lures.
5. Privacy First: Raw message text is NEVER stored or logged. Anonymized HMAC fingerprinting is used.
6. Responsible AI: Qualitative heuristic risk scores (5-98), never calibrated probabilities or 100% safe claims.
"""

import re
import os
import hmac
import hashlib
import unicodedata
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from urllib.parse import urlparse

# Maximum points any single category can contribute to the overall score
_CATEGORY_CAP = 40

# ── HMAC Fingerprinting Secret ────────────────────────────────────────────────
# Uses server secret if configured, with a stable fallback.
# Never logs raw content. Note: deterministic fingerprints still reveal identical repeat messages.
_DEFAULT_HMAC_SECRET = "scamshield-telemetry-isolation-key-v1"


def get_hmac_secret() -> str:
    """Retrieve HMAC secret key from environment or use default."""
    return os.environ.get("SCAMSHIELD_HMAC_SECRET", "").strip() or _DEFAULT_HMAC_SECRET


def hash_content(text: str, secret: Optional[str] = None) -> str:
    """
    Return a keyed HMAC-SHA256 fingerprint of the normalized text.
    Protects user privacy: raw message bodies are never stored or logged.
    Documentation note: HMAC fingerprints allow telemetry deduplication while preventing
    rainbow-table attacks, but identical messages still produce the same fingerprint.
    """
    sec = (secret or get_hmac_secret()).encode("utf-8")
    msg_bytes = text.encode("utf-8")
    return hmac.new(sec, msg_bytes, hashlib.sha256).hexdigest()


# ── Unicode Normalization & Obfuscation Handling ──────────────────────────────
# Invisible and zero-width characters commonly used to split keywords:
_ZERO_WIDTH_REGEX = re.compile(
    r"[\u200B-\u200D\uFEFF\u200E\u200F\u2060\u2000-\u200A\u00A0\u180E\u202F\u205F\u3000]"
)

# Common Cyrillic and Greek homoglyphs mapped to Latin equivalents
_HOMOGLYPH_MAP = {
    'а': 'a', 'е': 'e', 'о': 'o', 'р': 'p', 'с': 'c', 'у': 'y', 'х': 'x', 'і': 'i', 'ј': 'j',
    'А': 'A', 'В': 'B', 'Е': 'E', 'К': 'K', 'М': 'M', 'Н': 'H', 'О': 'O', 'Р': 'P', 'С': 'C',
    'Т': 'T', 'Х': 'X', 'Ү': 'Y',
}

# High-risk keywords commonly spaced out (e.g. "p a y p a l", "u r g e n t", "b i t c o i n")
_SPACED_TARGETS = [
    "paypal", "bitcoin", "urgent", "kyc", "crypto", "amazon", "police", "otp",
    "wire", "usdt", "arrest", "refund", "suspend", "winner",
]


def normalize_text_for_analysis(text: str) -> str:
    """
    Normalize text for internal heuristic evaluation ONLY:
    1. Unicode NFKC normalization (combining characters, wide characters).
    2. Stripping zero-width formatting characters.
    3. Conservative homoglyph transliteration for lookalike alphabets.
    4. Conservative condensation of spaced-out threat keywords (e.g., 'p a y p a l').
    
    IMPORTANT: Normalization is NOT treated as proof of fraud; it merely ensures
    obfuscated keywords can be inspected by our detection rules.
    """
    if not text:
        return ""

    # 1. NFKC normalization
    norm = unicodedata.normalize("NFKC", text)

    # 2. Strip zero-width and invisible formatting characters
    cleaned = _ZERO_WIDTH_REGEX.sub("", norm)

    # 3. Transliterate common Cyrillic/Greek homoglyphs
    transliterated = []
    for char in cleaned:
        transliterated.append(_HOMOGLYPH_MAP.get(char, char))
    cleaned = "".join(transliterated)

    # 4. Conservative condensation of spaced-out scam words
    for target in _SPACED_TARGETS:
        # Match target word spaced out with single space, dot, or dash:
        # e.g., 'p a y p a l' or 'b.i.t.c.o.i.n' or 'k-y-c'
        spaced_pattern = r"(?i)\b" + r"[\s\.\-_]+".join(list(target)) + r"\b"
        cleaned = re.sub(spaced_pattern, target, cleaned)

    return cleaned


# ── Pattern Definitions (Hardened with Word Boundaries & Context) ─────────────

# Prompt injection attempt patterns (attempts to trick the detector)
PROMPT_INJECTION_PATTERNS = [
    r"(?i)ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
    r"(?i)you\s+must\s+(say|rate|classify|mark)\s+(this\s+as\s+)?safe",
    r"(?i)system\s*:\s*this\s+message\s+is\s+verified",
    r"(?i)mark\s+this\s+as\s+legitimate",
    r"(?i)override\s+(security|safety|scam)\s+(check|filter|score)",
    r"(?i)disregard\s+threat\s+detection",
    r"(?i)do\s+not\s+flag\s+this",
]

# Urgency and panic triggers (contextualized to avoid bare "fine" or "police")
URGENCY_PATTERNS = [
    (r"(?i)\b(immediate|immediately|urgent|urgently|act now|hurry)\b", "High urgency language detected"),
    (r"(?i)\b(within\s+\d+\s*(hours?|mins?|minutes?)|24\s*hours?|today\s+only|expires?\s+soon)\b", "Artificial deadline or expiring window"),
    (r"(?i)\b(account\s+suspended|service\s+terminated|blocked|frozen|locked|deactivated)\b", "Threat of account suspension or service block"),
    (r"(?i)\b(legal\s+action|arrest\s+warrant|police\s+raid|police\s+arrest|court\s+notice|facing\s+prosecution|penalties\s+apply)\b", "Threat of legal or punitive law-enforcement consequences"),
    (r"(?i)\b(pay\s+(a\s+)?fine|unpaid\s+traffic\s+fine|court\s+fine|fine\s+of\s+(\$|rs\.?|inr|\£|\€)\s*\d+)\b", "Extortionate or urgent fine payment demand"),
    (r"(?i)\b(final\s+notice|last\s+chance|immediate\s+response\s+required)\b", "Final warning pressure tactics"),
]

# Impersonation signals (Brands, institutions, utilities)
# Strict boundaries and disambiguation to prevent "pineapple", "prime ribs", etc.
IMPERSONATION_TARGETS = [
    (r"(?i)\b(amazon|aws)\b|\bprime\s+(membership|account|subscription|delivery|service)\b", "Amazon"),
    (r"(?i)\b(paypal|venmo|zelle|cash\s*app|cashapp)\b", "Payment Provider"),
    (r"(?i)\b(chase(\s+bank)?|wells\s+fargo|bank\s+of\s+america|citi(\s*bank)?|hsbc|barclays|td\s*bank|sbi|hdfc|icici|axis\s*bank|pnb)\b", "Major Banking Institution"),
    (r"(?i)\b(fedex|ups|usps|dhl|royal\s*mail|courier|customs\s+clearance|delivery\s+agent)\b", "Postal / Courier Delivery Service"),
    # Disambiguate Apple from fruits (lookahead and lookbehind)
    (r"(?i)(?<![a-z])(apple|icloud)(?![a-z])|\b(google|microsoft|geek\s*squad|mcafee|norton)\b", "Tech / Software Support"),
    (r"(?i)\b(irs|hmrc|tax\s*department|social\s*security|ssa|govt|income\s*tax\s*department)\b", "Government / Tax Authority"),
    (r"(?i)\b(netflix|spotify|att|verizon|t-mobile)\b", "Telecom / Subscription Service"),
    (r"(?i)\b(cbi|ed|narcotics\s*control\s*bureau|ncb|trai|cyber\s*crime\s*cell)\b", "Law Enforcement / Regulatory Authority"),
]

# OTP: Disentangling Delivery from Theft
# Legitimate delivery: notification code provided to user with warning not to share
OTP_LEGITIMATE_DELIVERY_PATTERNS = [
    r"(?i)\b(?:your\s+)?(?:verification|security|login|otp|one[- ]time\s+password)\s+code\s+(?:is\s*:?\s*|\s*:?\s*)\d{4,8}\b",
    r"(?i)\buse\s+code\s+\d{4,8}\s+to\s+verify\b",
    r"(?i)\bvalid\s+for\s+\d+\s+minutes\b",
    r"(?i)\b(?:do\s*not|never|don\'?t)\s+share\s+(?:this\s+)?(?:code|otp|pin|password)\b",
]


def detect_otp_signals(text: str) -> Tuple[bool, List[str], bool]:
    """
    Evaluate OTP signals in text without lookbehind limitations.
    Disentangles genuine delivery (with defensive warnings) from active theft/harvesting.
    Returns:
      (otp_theft_detected, theft_descriptions, is_benign_delivery)
    """
    theft_flags: List[str] = []

    # 1. Direct request to reply with OTP/code
    if re.search(r"(?i)\breply\s+(?:immediately\s+|urgently\s+|now\s+|back\s+)?with\s+(?:the\s+)?(?:\d+[- ]digit\s+)?(?:code|otp|pin|password)\b", text) or \
       re.search(r"(?i)\breply\s+(?:immediately\s+|urgently\s+|now\s+)?.*?\b(?:otp|verification\s+code|security\s+code|passcode)\b", text):
        theft_flags.append("Direct request to reply with OTP code")

    # 2. Request to forward code
    if re.search(r"(?i)\bforward\s+(?:this\s+|the\s+)?(?:\d+[- ]digit\s+)?(?:code|otp|sms|message|passcode|authentication\s+code|verification\s+code)\b", text) or \
       re.search(r"(?i)\bforward\s+.*?\b(?:code|otp|passcode|pin)\b", text):
        theft_flags.append("Request to forward secret verification code")

    # 3. Request to share code (ONLY if NOT preceded by defensive warnings 'do not' / 'never')
    has_defensive_warning = bool(re.search(r"(?i)\b(?:do\s*not|never|don\'?t|should\s*not)\s+share\b", text))
    if not has_defensive_warning:
        if re.search(r"(?i)\bshare\s+(?:this\s+)?(?:code|otp|pin|password)\s+(?:with|to)\b", text) or \
           re.search(r"(?i)\b(?:please\s+)?share\s+(?:the\s+|your\s+)?(?:otp|code|pin)\b", text):
            theft_flags.append("Request to share secret code with another party")

    # 4. Solicit OTP to cancel/verify
    if re.search(r"(?i)\bprovide\s+(?:the|your)\s+(?:6|4)?[- ]?(?:digit\s+)?(?:code|otp|pin)\s+to\s+(?:cancel|verify|unblock|confirm)\b", text):
        theft_flags.append("Solicitation of OTP to cancel or verify transaction")

    # 5. Credential entry on URL
    if re.search(r"(?i)\benter\s+your\s+(?:password|credentials|pin)\s+at\s+http\b", text):
        theft_flags.append("Credential entry solicitation on external URL")

    # 6. UPI PIN fraud (India: entering PIN to receive money)
    if re.search(r"(?i)\b(?:enter|put|type|provide|input)\s+(?:your\s+)?(?:\d+[- ]digit\s+)?upi\s*pin\s+.*?\b(?:receive|claim|accept|credit|get|release)\b", text) or \
       re.search(r"(?i)\b(?:enter|put|type|provide|input)\s+(?:your\s+)?(?:\d+[- ]digit\s+)?upi\s*pin\s+to\s+(?:receive|claim|accept|credit|get)\b", text):
        theft_flags.append("Severe fraud: Requesting UPI PIN to receive money (PINs only send money)")

    # Benign delivery check
    is_benign = False
    for pat in OTP_LEGITIMATE_DELIVERY_PATTERNS:
        if re.search(pat, text):
            is_benign = True
            break

    otp_theft = len(theft_flags) > 0
    return otp_theft, theft_flags, is_benign

# Payment Pressure & Financial Demands
PAYMENT_PATTERNS = [
    (r"(?i)\b(gift\s*card|itunes\s*card|steam\s*card|google\s*play\s*card|vanilla\s*visa)\b", "High risk: Gift card payment requested"),
    (r"(?i)\b(bitcoin|crypto|usdt|eth|btc|wallet\s+address)\b", "High risk: Cryptocurrency payment requested"),
    (r"(?i)\b(wire\s+transfer|western\s*union|moneygram)\b", "Untraceable wire transfer requested"),
    (r"(?i)\b(unpaid\s+invoice|pending\s+bill|overdue\s+payment|debt\s+collection)\b", "Unsolicited invoice or debt collection claim"),
    (r"(?i)\b(clearance\s+fee|processing\s+fee\s+required|fee\s+to\s+release|registration\s+fee)\b", "Upfront fee requested to release funds or begin service"),
    (r"(?i)\b(collect\s+request\s+of\s+(rs\.?|inr|\$)\s*\d+.*(?:approve|accept)\s+on\s+(phonepe|gpay|paytm))\b", "Deceptive UPI collect request lure"),
]

# Prize, Lottery, Refund, and Delivery Lures (Contextualized to avoid isolated "winner")
LURE_PATTERNS = [
    (r"(?i)\b(lucky\s+winner|you\s+(have\s+)?won\s+(\$|rs\.?|inr|\£|\€)\s*\d+|selected\s+to\s+receive\s+(\$|rs\.?|\£|\€)\s*\d+|claim\s+your\s+prize|claim\s+your\s+jackpot|lottery\s+winner)\b", "Prize or sweepstakes lure with financial reward"),
    (r"(?i)\b(refund\s+of\s+(\$|rs\.?|inr|\£|\€)\s*\d+|overpaid|accidental\s+charge.*refund|reimbursement\s+pending)\b", "Unsolicited refund or overpayment lure"),
    (r"(?i)\b(unclaimed\s+package|package\s+pending\s+delivery|customs\s+fee\s+due|delivery\s+failed.*reschedule)\b", "Fake delivery package or customs fee lure"),
    (r"(?i)\b(inheritance|foreign\s+funds|beneficiary\s+of\s+(\$|rs\.?|\£)\s*\d+|next\s+of\s+kin)\b", "Inheritance / advance-fee fraud lure"),
    (r"(?i)\b(earn\s+(\$|rs\.?|inr|\£|\€)\s*\d+.*(?:daily|from\s+home|per\s+day)|part[- ]time\s+task|youtube\s+video\s+liking\s+job)\b", "Part-time task / fake work-from-home lure"),
]

# Regional Specific: India & Southeast Asia Acute Patterns
INDIA_REGIONAL_PATTERNS = [
    (r"(?i)\b(digital\s+arrest|cbi\s+cyber|mumbai\s+cyber\s+cell|skype\s+investigation|video\s+call\s+statement)\b", "India: Deceptive 'Digital Arrest' extortion scheme by fake law enforcement"),
    (r"(?i)\b(sbi|hdfc|icici|paytm|bank)\b.*\b(kyc\s+(expired|blocked|deactivated|suspended)|update\s+(pan|aadhaar))\b", "India: Bank KYC deactivation threat"),
    (r"(?i)\b(electricity\s+power\s+(will\s+be\s+)?disconnected\s+tonight|power\s+cut\s+at\s+9:30\s*pm)\b", "India: Electricity disconnection extortion scam"),
    (r"(?i)\b(install|download)\s+(anydesk|teamviewer|quicksupport|rustdesk|\.apk\b)\b", "Remote access tool or sideloaded APK installation solicitation"),
    (r"(?i)\b(lines?\s+will\s+be\s+disconnected|money\s+laundering\s+activities|narcotics\s+parcel)\b", "India: Telecom disconnection or narcotics extortion threat"),
]

# Suspicious Link Indicators
SUSPICIOUS_TLDS = {
    ".xyz", ".top", ".buzz", ".club", ".tk", ".ml", ".ga", ".cf", ".gq",
    ".work", ".click", ".link", ".rest", ".cam", ".live", ".loan", ".cfd", ".sbs"
}
SHORTENERS = {"bit.ly", "tinyurl.com", "t.co", "is.gd", "buff.ly", "ow.ly", "cutt.ly", "rb.gy"}

# Common file extensions that should NOT be parsed as URLs when appearing without scheme
FILE_EXTENSIONS = {
    "pdf", "docx", "doc", "xlsx", "xls", "pptx", "png", "jpg", "jpeg",
    "gif", "txt", "csv", "zip", "tar", "gz", "py", "js", "html", "css", "apk"
}

# Regex for URL candidates: handles http, https, www, bare IPv4, and domain with explicit path
_URL_CANDIDATE_REGEX = re.compile(
    r"(?i)"
    r"(?:"
    # 1. Standard scheme URLs (http, https) with domain or IPv4 + port + path
    r"https?://[^\s<>'\"{}|\\^`]+"
    r"|"
    # 2. www-prefixed URLs
    r"\bwww\d{0,3}\.[a-z0-9.\-]+\.[a-z]{2,10}(?::\d+)?(?:/[^\s<>'\"{}|\\^`]*)?"
    r"|"
    # 3. Direct IPv4 addresses with optional port and path
    r"\b(?:\d{1,3}\.){3}\d{1,3}(?::\d+)?(?:/[^\s<>'\"{}|\\^`]*)?"
    r"|"
    # 4. Domain with explicit forward slash path (e.g. example.com/login)
    r"\b[a-z0-9][a-z0-9.\-]*\.[a-z]{2,10}(?::\d+)?/[^\s<>'\"{}|\\^`]+"
    r")",
    re.IGNORECASE,
)

# Email address detector to avoid treating emails as URLs
_EMAIL_REGEX = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")


def extract_links(text: str) -> List[Dict[str, Any]]:
    """
    Extract and inspect URLs found within the text.
    Correctly handles:
      - http://, https://, www prefixes
      - IPv4 hosts with or without ports (e.g. http://192.168.1.1:8080/path)
      - Trailing punctuation (.,;:!?()[]{}"') embedded in prose
      - Internationalized domains (Punycode / IDN)
      - Excludes ordinary email addresses (e.g. user@example.com)
      - Excludes filenames (e.g. document.pdf, report.docx)
    """
    # 1. Find all email addresses so we can avoid treating them or their domains as standalone URLs
    email_matches = set(_EMAIL_REGEX.findall(text))

    raw_candidates = _URL_CANDIDATE_REGEX.findall(text)
    links_data = []
    seen_urls = set()

    for raw in raw_candidates:
        # Strip trailing punctuation commonly picked up in prose
        cleaned = raw.rstrip(".,;:!?()[]{}\"'<>")
        # Handle trailing unbalanced parens/brackets
        while cleaned.endswith(")") and "(" not in cleaned:
            cleaned = cleaned[:-1]
        while cleaned.endswith("]") and "[" not in cleaned:
            cleaned = cleaned[:-1]

        if not cleaned:
            continue

        # Skip if this candidate is an email address
        if cleaned in email_matches or any(cleaned in email for email in email_matches):
            continue

        # Ensure scheme for urlparse
        if cleaned.startswith(("http://", "https://")):
            parse_target = cleaned
        elif cleaned.startswith("www."):
            parse_target = "https://" + cleaned
        elif re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}", cleaned):
            parse_target = "http://" + cleaned
        else:
            parse_target = "https://" + cleaned

        try:
            parsed = urlparse(parse_target)
            hostname = parsed.hostname or ""
            domain = hostname.lower()

            if not domain or "." not in domain:
                continue

            # Check if this might be a simple filename like 'report.pdf' without real URL path
            parts = domain.split(".")
            tld = parts[-1].lower()
            if len(parts) == 2 and tld in FILE_EXTENSIONS and not parsed.path and not raw.startswith(("http://", "https://", "www.")):
                continue

            if cleaned in seen_urls:
                continue
            seen_urls.add(cleaned)

            flags = []
            is_suspicious = False

            # 1. Check for Direct IP address host
            is_ip = bool(re.match(r"^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$", domain))
            if is_ip:
                flags.append("Direct IP address used instead of reputable domain name")
                is_suspicious = True

            # 2. Check for URL shorteners
            if any(domain == s or domain.endswith("." + s) for s in SHORTENERS):
                flags.append("Obfuscated link (URL shortener hides true destination)")
                is_suspicious = True

            # 3. Check for Suspicious TLD
            for stld in SUSPICIOUS_TLDS:
                if domain.endswith(stld):
                    flags.append(f"Suspicious top-level domain ({stld})")
                    is_suspicious = True
                    break

            # 4. Check for Brand Lookalike / Typosquatting in domain or subdomain
            brands = ["amazon", "paypal", "apple", "chase", "netflix", "usps", "fedex", "google", "sbi", "hdfc"]
            for brand in brands:
                if brand in domain:
                    legit_suffixes = (
                        f"{brand}.com", f"{brand}.org", f"{brand}.co.uk", f"{brand}.ca",
                        f"{brand}.in", f"{brand}.co.in", f"{brand}.net"
                    )
                    # If brand is in domain but it's not a verified legitimate brand host
                    is_legit = any(domain == s or domain.endswith("." + s) for s in legit_suffixes)
                    if not is_legit:
                        flags.append(f"Lookalike brand spoofing ({brand} found in suspicious domain: {domain})")
                        is_suspicious = True

            # 5. Non-standard port flag (e.g. :8080, :5000, :8000 on external host)
            if parsed.port and parsed.port not in (80, 443):
                flags.append(f"Non-standard web port ({parsed.port})")
                is_suspicious = True

            # 6. Check for plain HTTP (not HTTPS)
            if raw.startswith("http://"):
                flags.append("Insecure plain HTTP link (no TLS encryption)")

            links_data.append({
                "url": cleaned,
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


def analyze_message(text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Primary analysis entry point for untrusted messages.
    Returns structured, explainable assessment with category breakdown.
    Guarantees:
      - Qualitative heuristic risk score (bounded between 5 and 98).
      - Never declares any message 100% safe.
      - Never logs raw message bodies.
      - Disentangles legitimate OTP delivery from malicious OTP harvesting.
      - Mitigates false positives from isolated words ('police', 'fine', 'winner', 'Prime', 'PIN').
    """
    if metadata is None:
        metadata = {}

    stripped = text.strip() if text else ""
    if not stripped:
        return {
            "error": "Empty message provided. Please paste the suspicious message text.",
            "status": "error"
        }

    # 1. Normalize text for analysis (NFKC, zero-width removal, homoglyph mapping)
    normalized = normalize_text_for_analysis(stripped)

    # 2. Prompt Injection Defense
    injection_attempt = detect_prompt_injection(normalized)

    # 3. Categorized Signal Collection
    signals: Dict[str, List[str]] = {
        "urgency": [],
        "impersonation": [],
        "suspicious_links": [],
        "otp_requests": [],
        "payment_pressure": [],
        "lures": [],
    }

    warning_signs: List[str] = []
    category_scores: Dict[str, int] = {}

    # Category A: Urgency
    urgency_pts = 0
    for pattern, desc in URGENCY_PATTERNS:
        if re.search(pattern, normalized):
            signals["urgency"].append(desc)
            if desc not in warning_signs:
                warning_signs.append(desc)
            urgency_pts += 20
    category_scores["urgency"] = min(urgency_pts, _CATEGORY_CAP)

    # Category B: Impersonation
    impersonated_entities = []
    impersonation_pts = 0
    for pattern, entity_name in IMPERSONATION_TARGETS:
        if re.search(pattern, normalized):
            note = f"Suspected impersonation of {entity_name}"
            signals["impersonation"].append(note)
            impersonated_entities.append(entity_name)
            if note not in warning_signs:
                warning_signs.append(note)
            impersonation_pts += 20
    category_scores["impersonation"] = min(impersonation_pts, _CATEGORY_CAP)

    # Category C: OTP Analysis — Disentangle Delivery vs. Theft
    otp_theft_detected, theft_descriptions, is_benign_delivery = detect_otp_signals(normalized)
    otp_pts = 0
    if otp_theft_detected:
        for desc in theft_descriptions:
            signals["otp_requests"].append(desc)
            if desc not in warning_signs:
                warning_signs.append(desc)
            otp_pts += 35

    category_scores["otp_requests"] = min(otp_pts, 55)

    # Category D: Payment Pressure
    payment_pts = 0
    for pattern, desc in PAYMENT_PATTERNS:
        if re.search(pattern, normalized):
            signals["payment_pressure"].append(desc)
            if desc not in warning_signs:
                warning_signs.append(desc)
            payment_pts += 30
    category_scores["payment_pressure"] = min(payment_pts, _CATEGORY_CAP)

    # Category E: Lures
    lure_pts = 0
    for pattern, desc in LURE_PATTERNS:
        if re.search(pattern, normalized):
            signals["lures"].append(desc)
            if desc not in warning_signs:
                warning_signs.append(desc)
            lure_pts += 25
    category_scores["lures"] = min(lure_pts, _CATEGORY_CAP)

    # Category F: Regional Indicators (India / SE Asia)
    regional_pts = 0
    for pattern, desc in INDIA_REGIONAL_PATTERNS:
        if re.search(pattern, normalized):
            if desc not in warning_signs:
                warning_signs.append(desc)
            regional_pts += 25
            # Attribute to relevant breakdown categories
            if "KYC" in desc or "Arrest" in desc:
                signals["urgency"].append(desc)
            if "APK" in desc or "Remote" in desc:
                signals["suspicious_links"].append(desc)

    # Category G: Suspicious Links
    extracted_links = extract_links(normalized)
    link_pts = 0
    for link in extracted_links:
        for f in link["flags"]:
            signals["suspicious_links"].append(f"{link['url']}: {f}")
            if f not in warning_signs:
                warning_signs.append(f)
            link_pts += 25
    category_scores["suspicious_links"] = min(link_pts, _CATEGORY_CAP)

    # ── Score Aggregation ─────────────────────────────────────────────────────
    base_points = sum(category_scores.values()) + min(regional_pts, 35)

    # Prompt injection detection adds security points
    if injection_attempt:
        warning_signs.insert(0, "Prompt injection attempt detected inside message payload")
        base_points += 35

    # Escalation Rule 1: Active OTP theft combined with urgency or brand impersonation
    if otp_theft_detected and (signals["impersonation"] or signals["urgency"] or signals["payment_pressure"]):
        base_points = max(base_points, 75)

    # Escalation Rule 2: Fake Digital Arrest / Law Enforcement extortion
    has_digital_arrest = any("Digital Arrest" in s for s in warning_signs)
    if has_digital_arrest:
        base_points = max(base_points, 85)

    # Escalation Rule 3: UPI PIN Deception
    has_upi_pin_fraud = any("UPI PIN" in s for s in warning_signs)
    if has_upi_pin_fraud:
        base_points = max(base_points, 80)

    # Legitimate Message Safety Dampener:
    # If the message is a legitimate OTP delivery (e.g. from Google/bank) and has NO theft signals,
    # NO suspicious links, and NO payment pressure, ensure it does NOT falsely escalate to HIGH RISK.
    if is_benign_delivery and not otp_theft_detected and not extracted_links and not signals["payment_pressure"]:
        # Benign service notice: do not count brand name as malicious impersonation
        signals["impersonation"] = []
        impersonated_entities = []
        warning_signs = [w for w in warning_signs if not w.startswith("Suspected impersonation")]
        base_points = min(base_points, 20)

    # Bound score between 5 and 98:
    # Minimum score 5 reflects foundational caution (no message is guaranteed 100% safe).
    # Maximum score 98 reflects qualitative heuristic limit.
    raw_score = max(5, min(98, base_points))

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
        summary_statement = "No obvious scam signals matched, but caution is always advised. Legitimate organizations will never ask for your passwords or OTPs."

    # Safe Next Steps
    safe_next_steps = [
        "Do NOT click any links, download attachments, or call numbers provided inside the message.",
        "Never share One-Time Passwords (OTP), 2FA codes, PINs, or banking passwords with anyone.",
        "If the message claims to be from an organization (e.g. Amazon, your bank), open your browser independently and log into your official account directly.",
        "Report and block the sender in your SMS or email app.",
    ]
    if signals["payment_pressure"]:
        safe_next_steps.insert(0, "Legitimate organizations NEVER demand payment via gift cards, cryptocurrency, or peer-to-peer apps.")
    if otp_theft_detected:
        safe_next_steps.insert(0, "CRITICAL WARNING: Real customer service will NEVER ask you to disclose, read back, or forward an OTP.")
    if has_digital_arrest:
        safe_next_steps.insert(0, "EMERGENCY: Police, CBI, and courts NEVER conduct 'digital arrests' over Skype or video calls. Hang up immediately.")
    if has_upi_pin_fraud:
        safe_next_steps.insert(0, "WARNING: Entering your UPI PIN ALWAYS transfers money OUT of your account. You NEVER enter a PIN to receive money.")

    suggested_response = generate_suggested_response(impersonated_entities, risk_level)

    # Privacy preservation: Keyed HMAC fingerprint of original message
    content_hash = hash_content(stripped)
    analyzed_at = datetime.now(timezone.utc).isoformat()

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
        "disclaimer": (
            "ScamShield uses defensive pattern heuristics — not a trained probability model. "
            "Scores are qualitative indicators, not calibrated probabilities. "
            "No automated system can guarantee a message is definitely safe. "
            "When in doubt, verify independently through official channels."
        ),
        "analysis_method": "heuristic_pattern_matching_v2",
        "prompt_injection_detected": injection_attempt,
        "links_found": len(extracted_links),
        "analyzed_at": analyzed_at,
    }
