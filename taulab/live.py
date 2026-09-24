"""Opt-in OpenAI-compatible adapter. Makes billable requests only in live mode."""

import json
import os
import time
import urllib.error
import urllib.request
from .benchmark import POLICY


def live_agent(request, call, ask, telemetry=None):
    if telemetry is None:
        telemetry = {}
    telemetry["usage"] = []
    telemetry["request_seconds"] = []
    key = os.environ.get("TAULAB_API_KEY")
    model = os.environ.get("TAULAB_MODEL")
    base = os.environ.get("TAULAB_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    telemetry.update(
        {"model": model, "base_url": base, "max_tokens": 512, "max_turns": 12}
    )
    if not key or not model:
        raise RuntimeError(
            "Set TAULAB_API_KEY and TAULAB_MODEL before running live mode"
        )
    specs = {
        "get_account": ("Read account data", {}),
        "get_policy": ("Read support policy", {}),
        "verify_identity": ("Verify user code", {"code": {"type": "string"}}),
        "change_plan": (
            "Change subscription plan",
            {"plan": {"type": "string", "enum": ["free", "starter", "pro"]}},
        ),
        "cancel_subscription": ("Cancel subscription", {}),
        "refund_invoice": ("Refund latest invoice", {"amount": {"type": "number"}}),
        "remove_member": ("Remove a team member", {"member": {"type": "string"}}),
        "export_data": ("Request data export", {}),
        "ask_user": (
            "Ask the user a clarification or verification question",
            {"message": {"type": "string"}},
        ),
    }
    definitions = [
        {
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": list(properties),
                    "additionalProperties": False,
                },
            },
        }
        for name, (description, properties) in specs.items()
    ]
    messages = [
        {
            "role": "system",
            "content": "You are a SaaS support agent. Complete the request according to this policy. Ask for verification using ask_user. Never invent a code.\n"
            + POLICY,
        },
        {"role": "user", "content": request},
    ]
    for turn in range(12):
        payload = {
            "model": model,
            "messages": messages,
            "tools": definitions,
            "temperature": 0,
            "max_tokens": 512,
        }
        req = urllib.request.Request(
            base + "/chat/completions",
            data=json.dumps(payload).encode(),
            headers={
                "Authorization": "Bearer " + key,
                "Content-Type": "application/json",
            },
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                data = json.load(response)
        except urllib.error.HTTPError as exc:
            raise RuntimeError(
                "Model endpoint returned HTTP " + str(exc.code)
            ) from None
        except urllib.error.URLError:
            raise RuntimeError("Model endpoint could not be reached") from None
        finally:
            telemetry["request_seconds"].append(time.perf_counter() - started)
        telemetry["usage"].append(data.get("usage"))
        telemetry["requests_completed"] = turn + 1
        message = data["choices"][0]["message"]
        messages.append(
            {k: v for k, v in message.items() if k in ("role", "content", "tool_calls")}
        )
        calls = message.get("tool_calls", [])
        if not calls:
            return message.get("content") or ""
        if len(calls) > 16:
            raise RuntimeError("Too many tool calls in one turn")
        for item in calls:
            name = item["function"]["name"]
            args = json.loads(item["function"]["arguments"])
            result = (
                {"response": ask(args["message"])}
                if name == "ask_user"
                else call(name, args)
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": item["id"],
                    "content": json.dumps(result),
                }
            )
    raise RuntimeError("Agent exceeded the 12-turn limit")
