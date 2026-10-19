"""
mcp_server/incident.py — ScamShield "Scam Incident Response" tools
===================================================================
Turns ScamShield from a one-shot message classifier into a stateful workflow:

    open_scam_case → add_evidence → start_live_call_coach / answer_coach_question
        → notify_family (confirm-gated) → build_report_pack

Design rules
  * Raw message text is never stored (only fingerprints, scores, short labels).
  * Voice summaries never read codes aloud and never call anything "100% safe".
  * Family alerts need explicit confirmation. If no webhook is configured the
    alert is queued in a local outbox and the tool says so honestly — it never
    claims delivery that did not happen.
"""

import os
import re
from typing import Any, Dict, List, Optional

import case_store as store

try:
    from analyzer import analyze_message
    from shared_constants import SAFE_NEXT_STEPS_DATA
except ImportError:  # pragma: no cover
    from backend.analyzer import analyze_message
    from backend.shared_constants import SAFE_NEXT_STEPS_DATA

DISCLAIMER = (
    "ScamShield gives defensive guidance, not certainty. Verify through official channels."
)

# ── Live-call coach: question bank (India "digital arrest"-style call scams) ──
# weight = how much a YES raises the risk score; critical = a YES alone is enough to escalate.
COACH_QUESTIONS: List[Dict[str, Any]] = [
    {"id": "authority", "weight": 25, "critical": False,
     "text": "Is the caller claiming to be police, CBI, customs, a court, TRAI, or another government officer?"},
    {"id": "accusation", "weight": 20, "critical": False,
     "text": "Are they saying you, your Aadhaar, your SIM, or a parcel is linked to a crime, drugs, or money laundering?"},
    {"id": "stay_on_call", "weight": 20, "critical": False,
     "text": "Are they telling you to stay on the video call or not to hang up?"},
    {"id": "secrecy", "weight": 25, "critical": True,
     "text": "Are they telling you not to tell your family or anyone else about this call?"},
    {"id": "money", "weight": 35, "critical": True,
     "text": "Are they asking you to transfer money, or move it to a safe or verification account?"},
    {"id": "credentials", "weight": 35, "critical": True,
     "text": "Are they asking for an OTP, your UPI PIN, or asking you to install a screen-sharing app?"},
    {"id": "time_pressure", "weight": 15, "critical": False,
     "text": "Are they threatening arrest or an account freeze if you do not act within minutes or hours?"},
]
_Q_BY_ID = {q["id"]: q for q in COACH_QUESTIONS}


_URL_RE = re.compile(r"(?:https?://\S+|\b[\w-]+(?:\.[\w-]+)+(?::\d+)?(?:/\S*)?)", re.IGNORECASE)
_DIGITS_RE = re.compile(r"\d{4,}")


def sanitize_signal(label: str) -> str:
    """Warning labels can quote the message (e.g. a scam domain). Strip links and long
    digit runs so nothing copied from the message is stored or forwarded."""
    label = _URL_RE.sub("[link]", label)
    return _DIGITS_RE.sub("[number]", label)


def _level_for(score: int) -> str:
    if score >= 60:
        return "HIGH RISK"
    if score >= 30:
        return "ELEVATED RISK"
    return "LOW RISK (Caution Still Advised)"


def _color_for(level: str) -> str:
    if level.startswith("HIGH"):
        return "#ef4444"
    if level.startswith("ELEVATED"):
        return "#f59e0b"
    return "#10b981"


def _card(title: str, level: str, score: int, bullets: List[str]) -> Dict[str, Any]:
    """Display card for screen-equipped devices (Echo Show / simulator)."""
    return {
        "type": "risk_card",
        "title": title,
        "risk_level": level,
        "risk_score": score,
        "color": _color_for(level),
        "bullets": bullets[:4],
    }


def _require_case(case_id: Any) -> Dict[str, Any]:
    if not isinstance(case_id, str) or not case_id.strip():
        raise ValueError("Missing 'case_id'. Open a case first with open_scam_case.")
    case = store.get_case(case_id.strip())
    if not case:
        raise ValueError(f"Unknown case_id '{case_id}'. Open a case first with open_scam_case.")
    return case


def _family(args: Dict[str, Any]) -> str:
    fam = args.get("family_id") or "default"
    if not isinstance(fam, str) or not re.fullmatch(r"[\w\-. ]{1,64}", fam):
        raise ValueError("family_id must be 1-64 letters, digits, spaces, dash, dot or underscore.")
    return fam


# ── Tool handlers ─────────────────────────────────────────────────────────────

def handle_open_case(args: Dict[str, Any]) -> Dict[str, Any]:
    family_id = _family(args)
    title = str(args.get("title") or "Suspicious contact").strip()[:120]
    case = store.create_case(family_id, title)
    return {
        "case_id": case["id"],
        "family_id": family_id,
        "status": case["status"],
        "voice_summary": "I have opened a new scam case. Send me the suspicious message, or tell me about the call.",
    }


def handle_add_evidence(args: Dict[str, Any]) -> Dict[str, Any]:
    case = _require_case(args.get("case_id"))
    message = args.get("message", "")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Missing or empty 'message' argument.")
    channel = args.get("channel", "sms")
    result = analyze_message(message.strip(), {"channel": channel})
    if result.get("status") == "error":
        raise ValueError(result.get("error", "Analysis failed."))

    fp = result["fingerprint"]
    seen_before = store.count_family_sightings(case["family_id"], fp, exclude_case=case["id"])
    store.add_evidence(
        case["id"], "message", fp, channel,
        int(result["risk_score"]), result["risk_level"],
        [sanitize_signal(w) for w in result.get("warning_signs", [])],
    )
    updated = store.get_case(case["id"])
    assert updated is not None

    repeat_note = ""
    if seen_before:
        repeat_note = f" This same message was already reported {seen_before} time(s) in your family."

    top = (result.get("warning_signs") or ["no overt fraud markers matched"])[0]
    top = re.sub(r"\b\d{4,8}\b", "[code redacted]", top)
    voice = (
        f"This looks like {result['risk_level']}, score {result['risk_score']} out of 100. "
        f"Main sign: {top}.{repeat_note} "
        + ("Do not click links or share codes. Want me to alert your family?"
           if result["risk_level"].startswith(("HIGH", "ELEVATED"))
           else "Caution is still advised. Never share codes with anyone.")
    )
    return {
        "case_id": case["id"],
        "risk_score": result["risk_score"],
        "risk_level": result["risk_level"],
        "warning_signs": result.get("warning_signs", []),
        "seen_before_in_family": seen_before,
        "case_max_risk": {"score": updated["max_score"], "level": updated["max_level"]},
        "evidence_count": len(updated["evidence"]),
        "prompt_injection_detected": result.get("prompt_injection_detected", False),
        "voice_summary": voice,
        "card": _card("Message check", result["risk_level"], int(result["risk_score"]),
                      list(result.get("warning_signs", []))),
        "disclaimer": DISCLAIMER,
    }


def _coach_state(answers: Dict[str, bool]) -> Dict[str, Any]:
    score = min(98, sum(_Q_BY_ID[q]["weight"] for q, yes in answers.items() if yes and q in _Q_BY_ID))
    critical_yes = [q for q, yes in answers.items() if yes and _Q_BY_ID.get(q, {}).get("critical")]
    level = "HIGH RISK" if (critical_yes or score >= 60) else _level_for(score)
    if critical_yes:
        score = max(score, 70)
    remaining = [q for q in COACH_QUESTIONS if q["id"] not in answers]
    done = level.startswith("HIGH") or not remaining
    return {
        "score": score, "level": level, "done": done,
        "next": None if done else remaining[0],
        "yes_signs": [_Q_BY_ID[q]["text"] for q, yes in answers.items() if yes and q in _Q_BY_ID],
    }


def _coach_response(case_id: str, answers: Dict[str, bool]) -> Dict[str, Any]:
    st = _coach_state(answers)
    if not st["done"]:
        q = st["next"]
        return {
            "case_id": case_id, "done": False,
            "risk_score": st["score"], "risk_level": st["level"],
            "question": {"id": q["id"], "text": q["text"]},
            "voice_summary": q["text"] + " Please answer yes or no.",
            "card": _card("Live call check", st["level"], st["score"], [q["text"]]),
            "disclaimer": DISCLAIMER,
        }

    if st["level"].startswith("HIGH"):
        script = (
            "Hang up now. Genuine police, CBI or courts do not arrest anyone over a video call "
            "or ask you to move money to a safe account. Do not share any code or PIN. "
            "Tell a family member right away. If any money was sent, call 1930 immediately."
        )
        steps = [
            "Hang up. Do not call the number back.",
            "Do not send money or share an OTP, UPI PIN, or install any app.",
            "Tell a family member now.",
            "If money was sent, call 1930 immediately and your bank's fraud helpline.",
        ]
    else:
        script = (
            "Nothing critical so far, but stay careful. If anyone asks for money, a code, "
            "or secrecy, hang up. You can always end the call and verify through an official number."
        )
        steps = [
            "End the call and verify through the organization's official number.",
            "Never share codes or PINs.",
            "Ask a family member to double-check with you.",
        ]
    store.set_status(case_id, "escalated" if st["level"].startswith("HIGH") else "open")
    return {
        "case_id": case_id, "done": True,
        "risk_score": st["score"], "risk_level": st["level"],
        "signs_found": st["yes_signs"],
        "safe_script": script,
        "next_steps": steps,
        "voice_summary": script,
        "card": _card("Live call verdict", st["level"], st["score"], steps),
        "disclaimer": DISCLAIMER,
    }


def handle_start_coach(args: Dict[str, Any]) -> Dict[str, Any]:
    case_id = args.get("case_id")
    if case_id:
        case = _require_case(case_id)
    else:
        case = store.create_case(_family(args), "Live suspicious call")
    store.save_coach_answers(case["id"], {})
    return _coach_response(case["id"], {})


def handle_answer_coach(args: Dict[str, Any]) -> Dict[str, Any]:
    case = _require_case(args.get("case_id"))
    qid = args.get("question_id")
    if qid not in _Q_BY_ID:
        raise ValueError(f"Unknown question_id '{qid}'. Valid: {list(_Q_BY_ID)}")
    answer = args.get("answer")
    if not isinstance(answer, bool):
        raise ValueError("'answer' must be true (yes) or false (no).")
    answers = store.get_coach_answers(case["id"])
    answers[qid] = answer
    store.save_coach_answers(case["id"], answers)
    resp = _coach_response(case["id"], answers)
    st = _coach_state(answers)
    if st["done"]:  # log one evidence row per finished coaching session
        store.add_evidence(
            case["id"], "call_coach", None, "voice_call",
            st["score"], st["level"], st["yes_signs"],
        )
    return resp


def handle_get_case(args: Dict[str, Any]) -> Dict[str, Any]:
    case = _require_case(args.get("case_id"))
    return {
        "case_id": case["id"], "family_id": case["family_id"], "title": case["title"],
        "status": case["status"],
        "max_risk": {"score": case["max_score"], "level": case["max_level"]},
        "evidence": case["evidence"], "alerts": case["alerts"],
        "voice_summary": (
            f"Case {case['title']} is {case['status']}, highest risk {case['max_level']}, "
            f"with {len(case['evidence'])} piece(s) of evidence."
        ),
    }


def _family_alert_text(case: Dict[str, Any], note: str) -> str:
    signs = []
    for e in case["evidence"]:
        for s in e["signals"]:
            if s not in signs:
                signs.append(s)
    signs_txt = "; ".join(signs[:3]) if signs else "suspicious contact reported"
    text = (
        f"ScamShield alert ({case['max_level']}, {case['max_score']}/100): {case['title']}. "
        f"Signs: {signs_txt}. Please call them now and tell them not to send money or share any code."
    )
    if note:
        text += f" Note: {note[:200]}"
    return text


def _deliver(text: str) -> Dict[str, str]:
    """Send via webhook if configured; otherwise honestly queue in the local outbox."""
    url = os.environ.get("SCAMSHIELD_WEBHOOK_URL", "").strip()
    if not url:
        return {"status": "queued_outbox", "delivery": "outbox_only"}
    try:
        import httpx
        r = httpx.post(url, json={"text": text, "content": text}, timeout=5.0)
        if r.status_code < 300:
            return {"status": "sent", "delivery": "webhook"}
        return {"status": "failed", "delivery": f"webhook_http_{r.status_code}"}
    except Exception as exc:  # network errors must not crash the tool
        return {"status": "failed", "delivery": f"webhook_error_{type(exc).__name__}"}


def handle_notify_family(args: Dict[str, Any]) -> Dict[str, Any]:
    case = _require_case(args.get("case_id"))
    note = str(args.get("note") or "").strip()
    confirm = args.get("confirm", False) is True  # strictly boolean True

    pending = store.get_pending_alert(case["id"])
    body = pending["body"] if pending else _family_alert_text(case, note)

    if not confirm:
        if not pending:
            store.add_alert(case["id"], "pending_confirmation", "none", body)
        return {
            "case_id": case["id"], "sent": False, "awaiting_confirmation": True,
            "preview": body,
            "voice_summary": "I can alert your family with this message. Do you want me to send it? Say yes to confirm.",
            "card": _card("Family alert preview", case["max_level"], case["max_score"], [body]),
        }

    if pending:
        alert_id = pending["id"]
    else:
        alert_id = store.add_alert(case["id"], "pending_confirmation", "none", body)
    res = _deliver(body)
    store.update_alert(alert_id, res["status"], res["delivery"])

    if res["status"] == "sent":
        voice = "Done. I alerted your family."
    elif res["status"] == "queued_outbox":
        voice = "I saved the alert, but no family channel is connected yet, so it was not delivered."
    else:
        voice = "I could not deliver the alert. Please call your family directly."
    return {
        "case_id": case["id"], "alert_id": alert_id,
        "sent": res["status"] == "sent", "status": res["status"], "delivery": res["delivery"],
        "preview": body, "voice_summary": voice,
    }


def handle_report_pack(args: Dict[str, Any]) -> Dict[str, Any]:
    case = _require_case(args.get("case_id"))
    resources = {
        k: v for k, v in SAFE_NEXT_STEPS_DATA["reporting_resources"].items() if k.startswith("India")
    }
    timeline = [
        f"{e['created_at']} — {e['kind']} via {e['channel'] or 'unknown'}: "
        f"{e['risk_level']} ({e['risk_score']}/100)"
        for e in case["evidence"]
    ]
    summary = (
        f"Case '{case['title']}' opened {case['created_at']}. Highest assessed risk: "
        f"{case['max_level']} ({case['max_score']}/100). {len(case['evidence'])} item(s) logged. "
        "Message contents are not stored by ScamShield; keep the original messages and screenshots yourself."
    )
    keep = [
        "Screenshots of the messages and the caller's number",
        "Date and time of each contact",
        "Transaction IDs, UTR numbers, and receiver account/UPI details if money was sent",
        "Your bank's name and the account or card used",
    ]
    steps = [
        "If money was sent, call 1930 immediately and your bank's fraud helpline.",
        "File a complaint on the National Cyber Crime Reporting Portal.",
        "Report suspicious numbers on the Chakshu portal.",
        "Keep every screenshot and transaction ID.",
    ]
    return {
        "case_id": case["id"], "complaint_summary": summary, "timeline": timeline,
        "what_to_keep": keep, "steps": steps, "reporting_resources": resources,
        "voice_summary": (
            "I prepared your report pack. If any money was sent, call 1930 right now, "
            "then file a complaint on the cyber crime portal."
        ),
        "disclaimer": DISCLAIMER + " Confirm current procedures on the official portals.",
    }


# ── Manifest (used by the JSON-RPC fallback and the docs) ─────────────────────

def _schema(props: Dict[str, Any], required: List[str]) -> Dict[str, Any]:
    return {"type": "object", "properties": props, "required": required}


INCIDENT_MANIFEST: List[Dict[str, Any]] = [
    {"name": "open_scam_case",
     "description": "Open a new scam case for a family so evidence and alerts persist across sessions.",
     "inputSchema": _schema({"family_id": {"type": "string"}, "title": {"type": "string"}}, [])},
    {"name": "add_evidence",
     "description": "Analyze a suspicious message and attach the result (not the text) to a case. Detects repeats across the family.",
     "inputSchema": _schema({"case_id": {"type": "string"}, "message": {"type": "string"},
                             "channel": {"type": "string", "default": "sms"}}, ["case_id", "message"])},
    {"name": "start_live_call_coach",
     "description": "Start a yes/no coaching session for a suspicious phone or video call happening right now.",
     "inputSchema": _schema({"family_id": {"type": "string"}, "case_id": {"type": "string"}}, [])},
    {"name": "answer_coach_question",
     "description": "Answer the current live-call coach question; risk builds across turns and ends with a safe script.",
     "inputSchema": _schema({"case_id": {"type": "string"}, "question_id": {"type": "string"},
                             "answer": {"type": "boolean"}}, ["case_id", "question_id", "answer"])},
    {"name": "get_scam_case",
     "description": "Fetch a case with its evidence timeline and alerts.",
     "inputSchema": _schema({"case_id": {"type": "string"}}, ["case_id"])},
    {"name": "notify_family",
     "description": "Alert the family about a case. Two steps: first call previews, second call with confirm=true sends.",
     "inputSchema": _schema({"case_id": {"type": "string"}, "note": {"type": "string"},
                             "confirm": {"type": "boolean", "default": False}}, ["case_id"])},
    {"name": "build_report_pack",
     "description": "Prepare a complaint summary, evidence checklist, and India reporting steps for a case.",
     "inputSchema": _schema({"case_id": {"type": "string"}}, ["case_id"])},
]

INCIDENT_HANDLERS = {
    "open_scam_case": handle_open_case,
    "add_evidence": handle_add_evidence,
    "start_live_call_coach": handle_start_coach,
    "answer_coach_question": handle_answer_coach,
    "get_scam_case": handle_get_case,
    "notify_family": handle_notify_family,
    "build_report_pack": handle_report_pack,
}
