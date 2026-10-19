"""
mcp_server/test_incident.py — unit tests for the stateful incident tools.
Run:  python -m unittest mcp_server/test_incident.py -v
"""
import json
import os
import sys
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "backend"))

import case_store  # noqa: E402
import incident  # noqa: E402

SCAM = "Dear customer your KYC is suspended, pay now at http://kyc-sbi.xyz or account blocked in 2 hrs"


class IncidentTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        case_store.set_db_path(os.path.join(self._tmp.name, "t.db"))
        os.environ.pop("SCAMSHIELD_WEBHOOK_URL", None)

    def tearDown(self):
        case_store.set_db_path(None)
        self._tmp.cleanup()

    def _case(self, fam="f1"):
        return incident.handle_open_case({"family_id": fam, "title": "t"})["case_id"]

    # ── evidence & privacy ──
    def test_raw_message_is_never_stored(self):
        cid = self._case()
        incident.handle_add_evidence({"case_id": cid, "message": SCAM})
        raw = Path(case_store.get_db_path()).read_bytes()
        self.assertNotIn(b"kyc-sbi.xyz", raw)
        self.assertNotIn(b"Dear customer", raw)

    def test_repeat_detection_is_scoped_to_family(self):
        a, b, other = self._case("fam"), self._case("fam"), self._case("stranger")
        incident.handle_add_evidence({"case_id": a, "message": SCAM})
        self.assertEqual(incident.handle_add_evidence({"case_id": b, "message": SCAM})["seen_before_in_family"], 1)
        self.assertEqual(incident.handle_add_evidence({"case_id": other, "message": SCAM})["seen_before_in_family"], 0)

    def test_voice_summary_never_reads_codes(self):
        cid = self._case()
        out = incident.handle_add_evidence({"case_id": cid, "message": "Your OTP is 493021, share it now to claim refund urgent"})
        self.assertNotIn("493021", out["voice_summary"])

    def test_validation_errors(self):
        with self.assertRaises(ValueError):
            incident.handle_add_evidence({"case_id": "nope", "message": "x"})
        with self.assertRaises(ValueError):
            incident.handle_add_evidence({"case_id": self._case(), "message": "  "})
        with self.assertRaises(ValueError):
            incident.handle_open_case({"family_id": "bad/../id"})

    # ── live-call coach ──
    def test_coach_escalates_on_critical_answer(self):
        cid = incident.handle_start_coach({"family_id": "f"})["case_id"]
        out = incident.handle_answer_coach({"case_id": cid, "question_id": "secrecy", "answer": True})
        self.assertTrue(out["done"])
        self.assertTrue(out["risk_level"].startswith("HIGH"))
        self.assertIn("1930", out["safe_script"])

    def test_coach_all_no_is_never_declared_safe(self):
        cid = incident.handle_start_coach({"family_id": "f"})["case_id"]
        out = None
        for q in incident.COACH_QUESTIONS:
            out = incident.handle_answer_coach({"case_id": cid, "question_id": q["id"], "answer": False})
        self.assertTrue(out["done"])
        self.assertTrue(out["risk_level"].startswith("LOW"))
        self.assertNotIn("100%", out["voice_summary"])
        self.assertNotIn("safe", out["risk_level"].lower())

    def test_coach_rejects_non_boolean_answer(self):
        cid = incident.handle_start_coach({"family_id": "f"})["case_id"]
        with self.assertRaises(ValueError):
            incident.handle_answer_coach({"case_id": cid, "question_id": "money", "answer": "yes"})

    def test_coach_state_persists_across_calls(self):
        cid = incident.handle_start_coach({"family_id": "f"})["case_id"]
        incident.handle_answer_coach({"case_id": cid, "question_id": "authority", "answer": True})
        nxt = incident.handle_answer_coach({"case_id": cid, "question_id": "accusation", "answer": False})
        self.assertEqual(nxt["question"]["id"], "stay_on_call")
        self.assertEqual(nxt["risk_score"], 25)

    # ── family alert ──
    def test_notify_requires_confirmation_and_is_honest_without_webhook(self):
        cid = self._case()
        incident.handle_add_evidence({"case_id": cid, "message": SCAM})
        prev = incident.handle_notify_family({"case_id": cid})
        self.assertTrue(prev["awaiting_confirmation"])
        self.assertFalse(prev["sent"])
        # truthy-but-not-True must NOT confirm
        still = incident.handle_notify_family({"case_id": cid, "confirm": "true"})
        self.assertFalse(still["sent"])
        done = incident.handle_notify_family({"case_id": cid, "confirm": True})
        self.assertEqual(done["status"], "queued_outbox")
        self.assertFalse(done["sent"])
        self.assertIn("not delivered", done["voice_summary"])

    def test_alert_text_has_no_raw_message(self):
        cid = self._case()
        incident.handle_add_evidence({"case_id": cid, "message": SCAM})
        prev = incident.handle_notify_family({"case_id": cid})
        self.assertNotIn("Dear customer", prev["preview"])

    def test_webhook_delivery(self):
        received = []

        class H(BaseHTTPRequestHandler):
            def do_POST(self):
                received.append(json.loads(self.rfile.read(int(self.headers["Content-Length"]))))
                self.send_response(200)
                self.end_headers()

            def log_message(self, *a):
                pass

        srv = HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        os.environ["SCAMSHIELD_WEBHOOK_URL"] = f"http://127.0.0.1:{srv.server_port}/hook"
        try:
            cid = self._case()
            incident.handle_add_evidence({"case_id": cid, "message": SCAM})
            out = incident.handle_notify_family({"case_id": cid, "confirm": True})
            self.assertTrue(out["sent"])
            self.assertEqual(out["delivery"], "webhook")
            self.assertEqual(len(received), 1)
            self.assertIn("ScamShield alert", received[0]["text"])
        finally:
            srv.shutdown()
            os.environ.pop("SCAMSHIELD_WEBHOOK_URL", None)

    def test_webhook_failure_is_reported_not_hidden(self):
        os.environ["SCAMSHIELD_WEBHOOK_URL"] = "http://127.0.0.1:9/unreachable"
        try:
            cid = self._case()
            out = incident.handle_notify_family({"case_id": cid, "confirm": True})
            self.assertFalse(out["sent"])
            self.assertEqual(out["status"], "failed")
        finally:
            os.environ.pop("SCAMSHIELD_WEBHOOK_URL", None)

    # ── report pack ──
    def test_report_pack(self):
        cid = self._case()
        incident.handle_add_evidence({"case_id": cid, "message": SCAM})
        pack = incident.handle_report_pack({"case_id": cid})
        self.assertTrue(all(k.startswith("India") for k in pack["reporting_resources"]))
        self.assertIn("1930", " ".join(pack["steps"]))
        self.assertEqual(len(pack["timeline"]), 1)


if __name__ == "__main__":
    unittest.main()
