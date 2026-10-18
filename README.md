# ScamShield

> **Heuristic scam-message inspection engine** — an explainable, privacy-first tool for detecting urgency manipulation, brand impersonation, OTP harvesting, and financial-fraud patterns across SMS, email, and payment notifications.

[![CI](https://github.com/YOUR_ORG/teampilot/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_ORG/teampilot/actions/workflows/ci.yml)

---

## Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Privacy Model](#privacy-model)
3. [Quick Start — Local Development](#quick-start--local-development)
4. [Quick Start — Docker](#quick-start--docker)
5. [Configuration Reference](#configuration-reference)
6. [Detection Engine — How it Works](#detection-engine--how-it-works)
7. [API Reference](#api-reference)
8. [MCP Server (Alexa+ / AI Assistant)](#mcp-server-alexa--ai-assistant)
9. [Evaluation & Benchmarks](#evaluation--benchmarks)
10. [Known Limitations](#known-limitations)
11. [Contributing](#contributing)

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│  Browser / Mobile Client                                        │
│  React + Vite SPA (frontend/)                                   │
│    ├── ScanMessageView — paste & analyze suspicious messages     │
│    ├── SafetyGuideView — 6-principle defensive literacy guide    │
│    ├── RecentChecksView — anonymized telemetry history          │
│    ├── FamilySafetyView — household awareness resources         │
│    └── SettingsView — backend connectivity diagnostics          │
└────────────────────┬────────────────────────────────────────────┘
                     │ REST (JSON)
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (backend/)                                     │
│    ├── main.py — lifespan, CORS, rate limiter, size limit       │
│    ├── analyzer.py — NFKC normalization, heuristic engine       │
│    ├── config.py — validated Pydantic settings                  │
│    ├── database.py — SQLite with set_db_path() test isolation   │
│    └── supabase_client.py — optional telemetry persistence      │
└────────────────────┬────────────────────────────────────────────┘
                     │ MCP stdio / streamable HTTP
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  MCP Server (mcp_server/)                                       │
│    └── server.py — official Python MCP SDK v2, voice summary   │
│        Tools: analyze_suspicious_message                        │
│               get_safe_next_steps                               │
│               get_sample_threat_cases                           │
└─────────────────────────────────────────────────────────────────┘
                     │ optional write / read
                     ▼
┌─────────────────────────────────────────────────────────────────┐
│  Storage Layer                                                  │
│    ├── SQLite (local dev, test isolation)                       │
│    └── Supabase PostgreSQL (production, optional)               │
│        — RLS enforced, service-role key server-side only        │
└─────────────────────────────────────────────────────────────────┘
```

---

## Privacy Model

| Guarantee | Implementation |
|-----------|----------------|
| Raw message never stored | `analyzer.py` stores only HMAC-SHA256 fingerprint + metadata |
| Raw message never logged | All log calls use `preview_length`, `fingerprint`, `risk_score` only |
| No silent downgrade | Frontend shows explicit error + opt-in offline button on API failure |
| Rate limiting | 60 requests / minute per IP (sliding window) |
| Payload cap | 64 KB maximum request body |
| CORS credentials + wildcard | Enforced: wildcard stripped when `allow_credentials=True` |
| Supabase key server-only | `SUPABASE_SERVICE_ROLE_KEY` never sent to browser or logged |

---

## Quick Start — Local Development

### Prerequisites

- Python 3.10+
- Node.js 18+

### Backend

```bash
# 1. Copy environment template
cp backend/.env.example backend/.env
#    Fill in HMAC_SECRET (required). SUPABASE_* are optional.

# 2. Install dependencies
pip install -r backend/requirements.txt

# 3. Run backend
uvicorn backend.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend

# 1. Copy env template
cp .env.example .env.local
#    Set VITE_API_BASE_URL=http://localhost:8000 (or leave default)

# 2. Install and run
npm install
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

### Run Tests

```bash
# Backend unit tests (38 tests, isolated temp DB)
python -m unittest backend/test_scamshield.py -v

# MCP server self-test (6 assertions)
python mcp_server/server.py --test

# Benchmark evaluation (26 labeled cases)
python evaluation/evaluate.py --verbose

# Frontend lint
cd frontend && npm run lint
```

---

## Quick Start — Docker

```bash
# 1. Configure secrets
cp .env.example .env
#    Edit .env — set HMAC_SECRET (required), SUPABASE_* (optional)

# 2. Build and run
VITE_API_BASE_URL=http://localhost:8000 docker compose up --build

# App available at http://localhost:8000
```

> **No secrets are baked into the image.** `HMAC_SECRET` and Supabase credentials are injected at container runtime from your `.env` file.

---

## Configuration Reference

| Variable | Required | Default | Description |
|---|---|---|---|
| `HMAC_SECRET` | **Yes** | — | 32+ char secret for HMAC-SHA256 message fingerprinting |
| `SUPABASE_URL` | No | `""` | Supabase project URL. If empty, SQLite is used. |
| `SUPABASE_SERVICE_ROLE_KEY` | No | `""` | Service-role key — **server-side only, never expose to browser** |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Comma-separated list of allowed browser origins |
| `RATE_LIMIT_PER_MINUTE` | No | `60` | Max analyze requests per IP per sliding window minute |
| `MAX_MESSAGE_BYTES` | No | `65536` | Maximum allowed request body size (64 KB) |
| `VITE_API_BASE_URL` | No | `http://localhost:8000` | Frontend build-time API URL |

Copy `.env.example` (root) or `backend/.env.example` to get started.

---

## Detection Engine — How it Works

The `analyzer.py` heuristic pipeline runs these stages in order:

1. **Input normalization** — Unicode NFKC, zero-width character stripping, Cyrillic/Greek homoglyph transliteration
2. **Prompt injection defense** — Detects override/bypass attempts inside message payload
3. **Spaced-out keyword reconstruction** — Collapses single-character spacing patterns (e.g. `p a y m e n t`)
4. **Signal collection** — Six categories: urgency, impersonation, suspicious links, OTP theft, payment pressure, lures
5. **OTP delivery vs. theft disambiguation** — Legitimate OTP delivery (with explicit "do not share" warning) is not flagged as theft; score is capped ≤ 20
6. **URL/link parsing** — Extracts bare hostnames, IPv4 addresses with ports, handles trailing punctuation, excludes email addresses and file extensions
7. **India-specific threat patterns** — UPI PIN fraud, digital arrest, KYC suspension, remote access tools, narcotics/telecom extortion
8. **HMAC-SHA256 fingerprinting** — Stores hash of normalized text only; raw message is discarded
9. **Score bounding** — Score bounded `[5, 98]`; never declares 100% safe

**Risk bands:**

| Score | Level |
|-------|-------|
| ≥ 60 | `HIGH RISK` |
| 30–59 | `ELEVATED RISK` |
| < 30 | `LOW RISK (Caution Still Advised)` |

---

## API Reference

All endpoints are versioned at `/api/v1/`.

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/status` | Backend + storage health check |
| `POST` | `/api/v1/analyze` | Analyze a suspicious message |
| `GET` | `/api/v1/safe-next-steps` | Emergency guidance and reporting portals |
| `GET` | `/api/v1/sample-cases` | Labeled sample test cases |
| `GET` | `/api/v1/history` | Anonymized scan telemetry history |

### `POST /api/v1/analyze`

```json
// Request
{
  "message": "Your OTP code is 493021. Never share this with anyone.",
  "channel": "sms",
  "save_history": true
}

// Response (200 OK)
{
  "status": "success",
  "fingerprint": "sha256:a3f1...",
  "risk_score": 20,
  "risk_level": "LOW RISK (Caution Still Advised)",
  "risk_color": "#10b981",
  "summary": "Appears to be a legitimate OTP delivery...",
  "warning_signs": [],
  "breakdown": { "urgency": [], "impersonation": [], "suspicious_links": [], "otp_requests": [], "payment_pressure": [], "lures": [] },
  "safe_next_steps": ["..."],
  "suggested_response": "...",
  "disclaimer": "...",
  "links_found": 0,
  "prompt_injection_detected": false
}
```

Rate limit: 60 requests / minute per IP. Exceeding returns `HTTP 429`.

---

## MCP Server (Alexa+ / AI Assistant)

The `mcp_server/server.py` implements the [Model Context Protocol (MCP)](https://spec.modelcontextprotocol.io/) using the official Python MCP SDK (`mcp>=2.3.0`).

> **Current status: Simulation / Development mode.** This server uses stdio transport and has been validated against MCP protocol v2024-11-05. Integration with a live Amazon Alexa+ skill or Google assistant requires additional OAuth, skill hosting, and account-linking configuration not included in this repository.

### Tools exposed

| Tool | Description |
|------|-------------|
| `analyze_suspicious_message` | Runs the ScamShield heuristic engine and returns voice-safe summary |
| `get_safe_next_steps` | Returns emergency guidance and official reporting portals |
| `get_sample_threat_cases` | Returns labeled sample threat cases for testing |

### Run locally

```bash
# Self-test (6 protocol assertions)
python mcp_server/server.py --test

# Stdio mode (for MCP client integration)
python mcp_server/server.py
```

---

## Evaluation & Benchmarks

The `evaluation/` directory contains a curated, labeled benchmark dataset and an honest evaluation script.

```bash
python evaluation/evaluate.py --verbose --threshold 30
```

Metrics reported: **Accuracy, Precision, Recall, F1 Score, FPR, FNR** — computed from real test runs, no invented numbers.

**Current results on 26-case benchmark (as of last run):**

| Metric | Value |
|--------|-------|
| Accuracy | 100% (26/26) |
| Precision | 100% |
| Recall | 100% |
| F1 Score | 1.0 |
| False Positive Rate | 0% |
| False Negative Rate | 0% |

> **Disclaimer:** These metrics reflect evaluation strictly on the curated 26-case test dataset, not proof or guarantee of real-world accuracy across open-domain threat traffic. Real-world performance will vary based on novel social engineering techniques, adversarial evasion, and evolving threat distributions.

---

## Known Limitations

| Limitation | Status |
|-----------|--------|
| Heuristic-only detection — no ML model | By design; keeps it interpretable and offline-capable |
| No live domain reputation lookup | Would require external API integration (VirusTotal, Google Safe Browsing) |
| No image/attachment scanning | Text-only analysis |
| Alexa+ skill not live | Simulation mode only; not deployed to Amazon skill store |
| OTP theft detection limited to English patterns | Non-English scam patterns partially covered via transliteration |
| 26-case benchmark is small | Expand `evaluation/benchmark_dataset.json` with more diverse cases |
| SQLite not suitable for multi-worker production | Use Supabase PostgreSQL for production horizontal scaling |

---

## Contributing

1. Never commit `.env` files or real secrets
2. Add test cases to `evaluation/benchmark_dataset.json` for new threat patterns
3. Keep `backend/shared_constants.py` as the single source of truth for `SAMPLE_CASES` and `SAFE_NEXT_STEPS_DATA`
4. Run the full test suite before opening a pull request:
   ```bash
   python -m unittest backend/test_scamshield.py -v
   python mcp_server/server.py --test
   python evaluation/evaluate.py
   cd frontend && npm run lint && npm run build
   ```
