"""
mcp_server/e2e_http_check.py — runtime proof for the Alexa+ track
==================================================================
Starts the real Streamable HTTP server in a subprocess, connects to it with the
OFFICIAL MCP Python client, and walks a full scam-incident flow:

  tools/list → add_evidence (twice, repeat detection) → live-call coach →
  notify_family (preview, then confirm) → build_report_pack

Run:  python mcp_server/e2e_http_check.py
Exit code 0 = everything passed. Used in CI and shown in the demo video.
"""

import asyncio
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def _wait_health(url: str, timeout: float = 20.0) -> dict:
    end = time.time() + timeout
    while time.time() < end:
        try:
            with urllib.request.urlopen(url, timeout=1) as r:
                return json.loads(r.read())
        except Exception:
            time.sleep(0.3)
    raise RuntimeError("server did not become healthy")


def _data(result) -> dict:
    """Extract the tool's dict from structured content (falls back to text)."""
    sc = getattr(result, "structured_content", None) or getattr(result, "structuredContent", None)
    if isinstance(sc, dict) and sc:
        return sc.get("result", sc) if set(sc) == {"result"} else sc
    return json.loads(result.content[0].text)


def check(cond: bool, label: str) -> None:
    print(("  PASS  " if cond else "  FAIL  ") + label)
    if not cond:
        raise SystemExit(1)


async def run(base: str) -> None:
    from mcp import Client

    async with Client(f"{base}/mcp") as client:
        print(f"negotiated protocol version: {client.protocol_version}")
        check(str(client.protocol_version) >= "2025-11-25", "protocol version >= 2025-11-25")

        tools = [t.name for t in (await client.list_tools()).tools]
        print("tools:", tools)
        for needed in ("analyze_suspicious_message", "open_scam_case", "add_evidence",
                       "start_live_call_coach", "answer_coach_question",
                       "notify_family", "build_report_pack"):
            check(needed in tools, f"tool exposed: {needed}")

        case = _data(await client.call_tool("open_scam_case", {"family_id": "demo", "title": "Fake KYC SMS"}))
        cid = case["case_id"]
        msg = "Dear customer your KYC is suspended, pay now at http://kyc-sbi.xyz or account blocked in 2 hrs"
        ev = _data(await client.call_tool("add_evidence", {"case_id": cid, "message": msg}))
        check(ev["risk_level"].startswith("HIGH"), f"scam SMS rated HIGH ({ev['risk_score']})")
        check("card" in ev and ev["card"]["type"] == "risk_card", "display card returned")

        case2 = _data(await client.call_tool("open_scam_case", {"family_id": "demo", "title": "Same SMS to mom"}))
        ev2 = _data(await client.call_tool("add_evidence", {"case_id": case2["case_id"], "message": msg}))
        check(ev2["seen_before_in_family"] == 1, "repeat scam recognised across cases (state persisted)")

        coach = _data(await client.call_tool("start_live_call_coach", {"family_id": "demo"}))
        ccid = coach["case_id"]
        check(coach["done"] is False and coach["question"]["id"] == "authority", "coach asks first question")
        for qid in ("authority", "accusation", "stay_on_call"):
            coach = _data(await client.call_tool(
                "answer_coach_question", {"case_id": ccid, "question_id": qid, "answer": True}))
        check(coach["risk_level"].startswith(("ELEVATED", "HIGH")), "risk builds across turns")
        coach = _data(await client.call_tool(
            "answer_coach_question", {"case_id": ccid, "question_id": "money", "answer": True}))
        check(coach["done"] and coach["risk_level"].startswith("HIGH"), "money request escalates to HIGH + safe script")
        check("1930" in coach["safe_script"], "safe script mentions 1930")

        prev = _data(await client.call_tool("notify_family", {"case_id": ccid}))
        check(prev["awaiting_confirmation"] and prev["sent"] is False, "family alert needs confirmation first")
        sent = _data(await client.call_tool("notify_family", {"case_id": ccid, "confirm": True}))
        check(sent["status"] in ("sent", "queued_outbox"), f"alert after confirm: {sent['status']} ({sent['delivery']})")
        if sent["status"] == "queued_outbox":
            check("not delivered" in sent["voice_summary"], "outbox mode is honest about non-delivery")

        pack = _data(await client.call_tool("build_report_pack", {"case_id": ccid}))
        check(any("India" in k for k in pack["reporting_resources"]), "report pack has India resources")

        bad = await client.call_tool("add_evidence", {"case_id": "case_nope", "message": "hi"})
        check(getattr(bad, "is_error", getattr(bad, "isError", False)), "unknown case -> structured error")


def main() -> None:
    port = _free_port()
    tmp = tempfile.mkdtemp()
    env = {**os.environ, "SCAMSHIELD_CASES_DB": os.path.join(tmp, "cases.db"),
           "SCAMSHIELD_HMAC_SECRET": "e2e-test-secret-e2e-test-secret-1234"}
    env.pop("SCAMSHIELD_WEBHOOK_URL", None)
    log_path = os.path.join(tmp, "server.log")
    log_file = open(log_path, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [sys.executable, str(ROOT / "mcp_server" / "server.py"), "--http", "--port", str(port)],
        env=env, stdout=log_file, stderr=subprocess.STDOUT, text=True,
    )
    try:
        base = f"http://127.0.0.1:{port}"
        health = _wait_health(f"{base}/health")
        print("health:", health["status"], f"({len(health['tools'])} tools)")
        with urllib.request.urlopen(f"{base}/simulator", timeout=5) as r:
            page = r.read().decode("utf-8")
        check(r.status == 200 and "ScamShield" in page and "/mcp" in page, "simulator page served at /simulator")
        asyncio.run(run(base))
        print("\nE2E HTTP CHECK PASSED")
    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
        log_file.close()


if __name__ == "__main__":
    main()
