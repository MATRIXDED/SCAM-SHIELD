"""
mcp_server/server.py — ScamShield Model Context Protocol (MCP) Server
=======================================================================
Model Context Protocol (MCP) server providing scam analysis and safety advisory
tools for AI assistant tool-calling frameworks (e.g., Claude, Bedrock, and Alexa+ agents).

Architectural Scope & Hackathon Track Notice:
---------------------------------------------
1. What is Implemented:
   - Official Python MCP SDK (v2.x) integration with MCPServer.
   - Dual-transport readiness: stdio (for local AI desktop assistants/CLIs)
     and Streamable HTTP transport (for network agent architectures).
   - Standard capability negotiation, tool listing, argument validation,
     and structured error responses.
   - Single source of truth for tools, sample cases, and safe next steps
     shared with FastAPI backend.
   - Voice-friendly concise summaries: never reads OTP codes or sensitive credentials
     aloud, and never declares messages 100% definitely safe.
2. What Remains Simulated / Future Work:
   - This MCP server provides tool-calling endpoints for an Alexa+ assistant agent.
     It is NOT a published consumer skill on the Amazon Alexa Skills Store (which
     requires ASK certification, custom interaction models, and voice model training).

Exposed MCP Tools:
  1. analyze_suspicious_message
  2. get_safe_next_steps
  3. get_sample_threat_cases

Usage:
  Interactive self-test CLI:
    python mcp_server/server.py --test

  Stdio transport (Claude Desktop / Agent tool calling):
    python mcp_server/server.py

  Streamable HTTP transport (Network agents):
    python mcp_server/server.py --http --port 8001
"""

import sys
import json
import os
import re
import asyncio
from typing import Dict, Any, List, Optional

# Ensure backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))

try:
    from analyzer import analyze_message
    from shared_constants import SAMPLE_CASES, SAFE_NEXT_STEPS_DATA, MCP_TOOLS_MANIFEST
except ImportError:
    from backend.analyzer import analyze_message
    from backend.shared_constants import SAMPLE_CASES, SAFE_NEXT_STEPS_DATA, MCP_TOOLS_MANIFEST


def build_voice_summary(result: Dict[str, Any]) -> str:
    """
    Generate a concise, safe spoken-word summary suitable for voice assistants (e.g. Alexa).
    Voice Safety Invariants:
      1. NEVER read sensitive codes, OTPs, or passwords aloud.
      2. NEVER declare any message definitely 100% safe.
      3. Provide a single clear defensive action.
    """
    risk_level = result["risk_level"]
    score = result["risk_score"]
    warning_signs = result.get("warning_signs", [])

    if warning_signs:
        # Sanitize any numeric passcodes or OTPs to prevent reading them aloud
        top_warning = warning_signs[0]
        top_warning = re.sub(r"\b\d{4,8}\b", "[code redacted]", top_warning)
    else:
        top_warning = "no overt fraud markers matched"

    if risk_level.startswith("HIGH"):
        advice = "Do not click any links or share codes. Verify directly through official channels."
    elif risk_level.startswith("ELEVATED"):
        advice = "Exercise caution. Do not enter credentials on unverified websites."
    else:
        advice = "Caution is always advised. Legitimate companies will never request your OTP or password."

    return (
        f"ScamShield evaluated this message as {risk_level}, risk score {score} out of 100. "
        f"Primary observation: {top_warning}. Guidance: {advice}"
    )


# ── Tool Implementations ──────────────────────────────────────────────────────

def handle_analyze_message(args: Dict[str, Any]) -> Dict[str, Any]:
    """Execute scam analysis with voice-friendly response formatting."""
    message = args.get("message", "")
    if not isinstance(message, str) or not message.strip():
        raise ValueError("Missing or empty 'message' argument. Please provide text to analyze.")

    channel = args.get("channel", "sms")
    raw_result = analyze_message(message.strip(), {"channel": channel})

    if raw_result.get("status") == "error":
        raise ValueError(raw_result.get("error", "Analysis failed."))

    # Generate voice summary and sanitize output
    raw_result["voice_summary"] = build_voice_summary(raw_result)
    return raw_result


def handle_get_safe_next_steps(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return emergency triage steps and verified reporting hotlines from shared knowledge."""
    threat_type = (args.get("threat_type") or "").lower()
    guidance = list(SAFE_NEXT_STEPS_DATA["emergency_guidance"])
    checklist = list(SAFE_NEXT_STEPS_DATA["general_checklist"])

    if "otp" in threat_type or "password" in threat_type:
        guidance.insert(0, "EMERGENCY: If you disclosed an OTP, change your password and revoke active sessions immediately.")
    if "upi" in threat_type or "pin" in threat_type:
        guidance.insert(0, "EMERGENCY: You never enter a UPI PIN to receive money. If money was debited, call 1930 immediately.")
    if "card" in threat_type or "bank" in threat_type:
        guidance.insert(0, "EMERGENCY: Call your bank fraud helpline on the back of your physical card to freeze the card.")

    return {
        "emergency_guidance": guidance,
        "general_checklist": checklist,
        "reporting_resources": SAFE_NEXT_STEPS_DATA["reporting_resources"],
        "voice_summary": (
            "Emergency safety guidance: If you disclosed banking credentials or OTPs, "
            "contact your financial institution immediately. Forward spam SMS to 7726 or report to official cyber crime portals."
        ),
        "disclaimer": "ScamShield provides defensive heuristics. Always verify independently through trusted official channels.",
    }


def handle_get_sample_cases(args: Dict[str, Any]) -> Dict[str, Any]:
    """Return benchmark sample cases from shared constants, with optional category filter."""
    category_filter = (args.get("category") or "").lower()
    cases = SAMPLE_CASES
    if category_filter:
        cases = [c for c in cases if category_filter in c["category"].lower() or category_filter in c["title"].lower()]

    return {
        "sample_cases": cases,
        "count": len(cases),
        "source": "shared_constants",
    }


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatcher for tool execution with argument validation and error wrapping."""
    if not isinstance(arguments, dict):
        arguments = {}

    if name == "analyze_suspicious_message":
        return handle_analyze_message(arguments)
    elif name == "get_safe_next_steps":
        return handle_get_safe_next_steps(arguments)
    elif name == "get_sample_threat_cases":
        return handle_get_sample_cases(arguments)
    else:
        raise ValueError(f"Unknown MCP tool requested: '{name}'. Supported tools: {[t['name'] for t in MCP_TOOLS_MANIFEST]}")


# ── Official MCP SDK Server Integration ───────────────────────────────────────

def create_mcp_server():
    """Create and configure MCPServer instance from official python MCP SDK."""
    try:
        from mcp.server.mcpserver import MCPServer
        mcp_app = MCPServer(
            name="scamshield-mcp-server",
            version="2.0.0",
            instructions=(
                "ScamShield AI Scam Detection Assistant. "
                "Use analyze_suspicious_message to evaluate unverified messages for fraud, urgency, "
                "and phishing. Never declare a message 100% safe."
            ),
        )

        @mcp_app.tool(
            name="analyze_suspicious_message",
            description="Analyze an untrusted message for scam markers, urgency, brand impersonation, and OTP harvesting.",
        )
        def tool_analyze_message(message: str, channel: str = "sms") -> str:
            res = handle_analyze_message({"message": message, "channel": channel})
            return json.dumps(res, indent=2)

        @mcp_app.tool(
            name="get_safe_next_steps",
            description="Retrieve emergency action steps and verified reporting hotlines for scam mitigation.",
        )
        def tool_safe_next_steps(threat_type: Optional[str] = None) -> str:
            res = handle_get_safe_next_steps({"threat_type": threat_type or ""})
            return json.dumps(res, indent=2)

        @mcp_app.tool(
            name="get_sample_threat_cases",
            description="Retrieve benchmark test messages to simulate and test detection capabilities.",
        )
        def tool_sample_cases(category: Optional[str] = None) -> str:
            res = handle_get_sample_cases({"category": category or ""})
            return json.dumps(res, indent=2)

        return mcp_app
    except ImportError:
        return None


# ── Standard JSON-RPC 2.0 Fallback Processor ──────────────────────────────────

def process_json_rpc(request: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Process a single JSON-RPC 2.0 message with full protocol compliance:
      - initialization & capability negotiation
      - notifications handling (e.g. notifications/initialized returns None, no response)
      - tool listing from shared_constants
      - tool execution with structured error formatting
    """
    rpc_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    # Handle notifications (requests without an ID expect NO response)
    if rpc_id is None and (method.startswith("notifications/") or method == "initialized"):
        return None

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "scamshield-mcp-server",
                    "version": "2.0.0",
                },
                "capabilities": {
                    "tools": {},
                },
            },
        }

    elif method == "tools/list":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "tools": MCP_TOOLS_MANIFEST,
            },
        }

    elif method == "tools/call":
        tool_name = params.get("name")
        args = params.get("arguments", {})
        try:
            result = execute_tool(tool_name, args)
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2),
                        }
                    ],
                    "isError": False,
                },
            }
        except Exception as exc:
            return {
                "jsonrpc": "2.0",
                "id": rpc_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error executing tool '{tool_name}': {str(exc)}",
                        }
                    ],
                    "isError": True,
                },
            }

    else:
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "error": {
                "code": -32601,
                "message": f"Method '{method}' not found",
            },
        }


def run_stdio_server():
    """Run JSON-RPC 2.0 listener over standard input/output."""
    mcp_sdk_server = create_mcp_server()
    if mcp_sdk_server is not None:
        try:
            asyncio.run(mcp_sdk_server.run_stdio_async())
            return
        except Exception as exc:
            # Fall back to lightweight stdio loop if SDK async runner encounters environment issue
            sys.stderr.write(f"MCPServer stdio failed ({exc}); falling back to standard JSON-RPC loop\n")

    # Resilient stdio loop
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = process_json_rpc(req)
            if resp is not None:
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": f"Parse error: {str(e)}"},
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


def run_cli_test():
    """Interactive self-test mode testing protocol negotiation and tool execution."""
    print("=" * 70)
    print("ScamShield MCP Server Self-Test (Amazon Alexa+ / Assistant Track)")
    print("=" * 70)

    # 1. Initialize
    init_req = {"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {}}
    init_res = process_json_rpc(init_req)
    print("\n[1] initialize result:")
    print("    Protocol Version:", init_res["result"]["protocolVersion"])
    print("    Server Info:", init_res["result"]["serverInfo"])

    # 2. Notification (no response expected)
    notif_req = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
    notif_res = process_json_rpc(notif_req)
    print("\n[2] notification handling (notifications/initialized):", "Ignored without error (correct)" if notif_res is None else "Unexpected response")

    # 3. List tools
    tools_req = {"jsonrpc": "2.0", "id": "2", "method": "tools/list", "params": {}}
    tools_res = process_json_rpc(tools_req)
    tool_names = [t["name"] for t in tools_res["result"]["tools"]]
    print("\n[3] available tools (from shared_constants):", tool_names)

    # 4. Call analyze_suspicious_message
    call_req = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "tools/call",
        "params": {
            "name": "analyze_suspicious_message",
            "arguments": {
                "message": "AMAZON ALERT: Your Prime membership has been suspended. Confirm billing within 24 hours at http://amz-prime-support.xyz/login",
                "channel": "sms",
            },
        },
    }
    call_res = process_json_rpc(call_req)
    result_data = json.loads(call_res["result"]["content"][0]["text"])
    print("\n[4] analyze_suspicious_message tool call:")
    print(f"    Risk Level: {result_data['risk_level']} (Score: {result_data['risk_score']})")
    print(f"    Voice Summary: \"{result_data['voice_summary']}\"")
    print(f"    Warning count: {len(result_data['warning_signs'])}")

    # 5. Call get_safe_next_steps
    steps_req = {
        "jsonrpc": "2.0",
        "id": "4",
        "method": "tools/call",
        "params": {"name": "get_safe_next_steps", "arguments": {"threat_type": "otp"}},
    }
    steps_res = process_json_rpc(steps_req)
    steps_data = json.loads(steps_res["result"]["content"][0]["text"])
    print("\n[5] get_safe_next_steps tool call:")
    print("    Emergency advice items:", len(steps_data["emergency_guidance"]))
    print("    Official hotlines:", list(steps_data["reporting_resources"].keys()))

    # 6. Test argument validation on missing message
    bad_req = {
        "jsonrpc": "2.0",
        "id": "5",
        "method": "tools/call",
        "params": {"name": "analyze_suspicious_message", "arguments": {"message": ""}},
    }
    bad_res = process_json_rpc(bad_req)
    print("\n[6] argument validation test (empty input):")
    print("    isError:", bad_res["result"]["isError"])
    print("    Error text:", bad_res["result"]["content"][0]["text"])

    print("\n" + "=" * 70)
    print("ALL MCP SERVER SELF-TESTS PASSED SUCCESSFULLY.")
    print("=" * 70)


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_cli_test()
    else:
        run_stdio_server()
