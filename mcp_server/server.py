"""
mcp_server/server.py — ScamShield Model Context Protocol (MCP) Server
=======================================================================
Modular MCP server providing scam analysis and safety advisory tools
for AI assistants, command centers, and Amazon Alexa+ simulated skill agents.

Compliant with standard MCP JSON-RPC 2.0 protocol over stdio.

Tools exposed:
  1. analyze_suspicious_message
  2. get_safe_next_steps
  3. get_sample_threat_cases

Usage:
  Direct stdio mode:
    python mcp_server/server.py

  Interactive test / CLI mode:
    python mcp_server/server.py --test
"""

import sys
import json
import os
from typing import Dict, Any, List

# Ensure backend modules can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "backend")))
try:
    from analyzer import analyze_message
except ImportError:
    # Standalone fallback if invoked in isolation
    from backend.analyzer import analyze_message


MCP_TOOLS_MANIFEST = [
    {
        "name": "analyze_suspicious_message",
        "description": (
            "Analyze an untrusted SMS, email, or payment notification for signs of fraud, "
            "urgency manipulation, brand impersonation, deceptive URLs, OTP harvesting, "
            "and extortion. Never treats input as definitely safe."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {
                    "type": "string",
                    "description": "The exact untrusted suspicious text to evaluate.",
                },
                "channel": {
                    "type": "string",
                    "enum": ["sms", "email", "payment_app", "other"],
                    "description": "Communication channel where message was observed.",
                    "default": "sms",
                },
            },
            "required": ["message"],
        },
    },
    {
        "name": "get_safe_next_steps",
        "description": (
            "Retrieve immediate safety recommendations, emergency actions for compromised "
            "credentials, and official verification links for legitimate institutions."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "threat_type": {
                    "type": "string",
                    "description": "Optional category of threat (e.g. otp, banking, amazon_impersonation, gift_card)",
                }
            },
        },
    },
    {
        "name": "get_sample_threat_cases",
        "description": "Retrieve benchmark test messages to simulate and verify scam detection capabilities.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def handle_analyze_message(args: Dict[str, Any]) -> Dict[str, Any]:
    text = args.get("message", "")
    channel = args.get("channel", "sms")
    return analyze_message(text, {"channel": channel})


def handle_get_safe_next_steps(args: Dict[str, Any]) -> Dict[str, Any]:
    threat_type = args.get("threat_type", "").lower()
    guidance = [
        "Do NOT click any links, open attachments, or call phone numbers in the message.",
        "Never disclose One-Time Passwords (OTP), 2FA codes, or passwords to anyone.",
        "Independently open your browser and navigate directly to official websites.",
        "Forward phishing SMS messages to 7726 (SPAM) to inform carrier fraud filters.",
    ]
    if "otp" in threat_type or "password" in threat_type:
        guidance.insert(0, "EMERGENCY: If you disclosed an OTP, change your account password and revoke active sessions immediately.")
    if "card" in threat_type or "bank" in threat_type:
        guidance.insert(0, "EMERGENCY: Call your bank fraud line on the back of your physical card to freeze the compromised account.")
    
    return {
        "recommended_actions": guidance,
        "official_reporting_portals": {
            "Amazon Phishing Report": "https://www.amazon.com/gp/help/customer/display.html?nodeId=GRGRY7AQ3LMPXNCR",
            "US FTC Fraud Report": "https://reportfraud.ftc.gov",
            "US FBI IC3": "https://www.ic3.gov",
        },
        "disclaimer": "ScamShield provides defensive heuristics. Always verify independently through trusted official channels.",
    }


def handle_get_sample_cases(args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sample_cases": [
            {
                "id": "amz-prime-suspension",
                "label": "Amazon Prime Phishing",
                "text": "AMAZON ALERT: Your Prime subscription is suspended. Update billing within 24 hours at http://amz-prime-support.xyz/login",
            },
            {
                "id": "chase-otp-theft",
                "label": "Bank OTP Interception",
                "text": "CHASE SECURITY: A charge of $842.19 is pending. Reply with the 6-digit OTP code sent to your phone to cancel this transfer.",
            },
            {
                "id": "legit-doctor-reminder",
                "label": "Legitimate Doctor Appointment",
                "text": "Reminder: Your annual checkup with Dr. Reynolds is scheduled for tomorrow at 10:30 AM. Reply 1 to confirm.",
            },
        ]
    }


def execute_tool(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    if name == "analyze_suspicious_message":
        return handle_analyze_message(arguments)
    elif name == "get_safe_next_steps":
        return handle_get_safe_next_steps(arguments)
    elif name == "get_sample_threat_cases":
        return handle_get_sample_cases(arguments)
    else:
        raise ValueError(f"Unknown MCP tool requested: {name}")


def process_json_rpc(request: Dict[str, Any]) -> Dict[str, Any]:
    """Process a single JSON-RPC 2.0 message."""
    rpc_id = request.get("id")
    method = request.get("method")
    params = request.get("params", {})

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rpc_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": "scamshield-mcp-server",
                    "version": "1.0.0",
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
                            "text": f"Error executing {tool_name}: {str(exc)}",
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
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            resp = process_json_rpc(req)
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
    """Interactive self-test mode."""
    print("==================================================================")
    print("ScamShield MCP Server Self-Test (Modular Assistant / Alexa+ Track)")
    print("==================================================================")
    
    # 1. Initialize
    init_req = {"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {}}
    init_res = process_json_rpc(init_req)
    print("\n[1] initialize result:", json.dumps(init_res["result"]["serverInfo"]))

    # 2. List tools
    tools_req = {"jsonrpc": "2.0", "id": "2", "method": "tools/list", "params": {}}
    tools_res = process_json_rpc(tools_req)
    tools = [t["name"] for t in tools_res["result"]["tools"]]
    print("\n[2] available tools:", tools)

    # 3. Call analyze_suspicious_message
    call_req = {
        "jsonrpc": "2.0",
        "id": "3",
        "method": "tools/call",
        "params": {
            "name": "analyze_suspicious_message",
            "arguments": {
                "message": "AMAZON ALERT: Your account is locked! Click http://amazon-verify-login.xyz to restore within 1 hour.",
                "channel": "sms",
            },
        },
    }
    call_res = process_json_rpc(call_req)
    result_text = call_res["result"]["content"][0]["text"]
    parsed = json.loads(result_text)
    print("\n[3] analyze_suspicious_message call:")
    print(f"    Risk Level: {parsed['risk_level']} (Score: {parsed['risk_score']})")
    print(f"    Warning signs detected: {len(parsed['warning_signs'])}")
    for w in parsed["warning_signs"]:
        print(f"     - {w}")
    print("\nMCP Server test completed successfully.")


if __name__ == "__main__":
    if "--test" in sys.argv:
        run_cli_test()
    else:
        run_stdio_server()
