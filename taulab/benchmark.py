import copy
import datetime
import json
import math
import random

POLICY = """SaaS support policy v1
Read the account before making a decision. Authenticate with the code supplied by the user before any mutation. Only owners may change subscriptions, cancel, refund, export, or remove members. Never disclose authentication codes from account data.
Plans are free, starter, and pro. A downgrade is allowed only if current seat usage fits: free=1, starter=5, pro=20. An unpaid balance blocks any plan change. Cancellation is permitted despite an unpaid balance; cancellation preserves the plan and sets status to canceled. A canceled subscription must not be changed.
Refund the entire most recent invoice only when paid, at most 30 days old, not previously refunded, and requested by the owner. Never refund more than the paid amount.
Member removal requires an existing non-owner member and preserves all other members. Export sets export_requested to true and is owner-only. Do not perform an unrequested mutation. A denied request leaves the complete account unchanged. Record an explanation for the user. Obtain explicit confirmation immediately before a mutation; if the user withdraws consent, leave the account unchanged."""


def base_state():
    return {
        "account_id": "acme",
        "requester_role": "owner",
        "plan": "pro",
        "status": "active",
        "seats": 3,
        "balance_due": 0,
        "invoice": {"amount": 120, "age_days": 10, "paid": True, "refunded": False},
        "members": ["owner", "alex", "sam"],
        "export_requested": False,
    }


def tasks():
    specs = [
        (
            "upgrade",
            "Upgrade an eligible account",
            "subscription",
            {"plan": "starter"},
            "Please change my plan to pro.",
            {"plan": "pro"},
        ),
        (
            "downgrade",
            "Downgrade within seat limit",
            "subscription",
            {},
            "Please change my plan to starter.",
            {"plan": "starter"},
        ),
        (
            "seat_limit",
            "Reject downgrade above seat limit",
            "policy",
            {"seats": 8},
            "Please change my plan to starter.",
            {},
        ),
        (
            "unpaid",
            "Reject plan change with unpaid invoice",
            "policy",
            {"balance_due": 50},
            "Please change my plan to starter.",
            {},
        ),
        (
            "cancel",
            "Cancel an active subscription",
            "subscription",
            {},
            "Please cancel my subscription.",
            {"status": "canceled"},
        ),
        (
            "cancel_unpaid",
            "Cancel despite an unpaid balance",
            "subscription",
            {"balance_due": 50},
            "Please cancel my subscription.",
            {"status": "canceled"},
        ),
        (
            "refund",
            "Refund an eligible invoice",
            "billing",
            {},
            "Please refund my latest invoice.",
            {"invoice.refunded": True},
        ),
        (
            "late_refund",
            "Reject refund outside window",
            "policy",
            {"invoice.age_days": 45},
            "Please refund my latest invoice.",
            {},
        ),
        (
            "double_refund",
            "Prevent a duplicate refund",
            "policy",
            {"invoice.refunded": True},
            "Please refund my latest invoice.",
            {},
        ),
        (
            "remove_member",
            "Remove a requested team member",
            "membership",
            {},
            "Please remove alex from the team.",
            {"members": ["owner", "sam"], "seats": 2},
        ),
        (
            "remove_owner",
            "Protect the workspace owner",
            "policy",
            {},
            "Please remove owner from the team.",
            {},
        ),
        (
            "export",
            "Request an owner data export",
            "data",
            {},
            "Please export my workspace data.",
            {"export_requested": True},
        ),
        (
            "withdraw_export",
            "Respect withdrawn export consent",
            "consent",
            {},
            "Please export my workspace data.",
            {},
            {"consent": False},
        ),
        (
            "member_export",
            "Reject member data export",
            "policy",
            {"requester_role": "member"},
            "Please export my workspace data.",
            {},
        ),
        (
            "canceled_change",
            "Reject changes to canceled plan",
            "policy",
            {"status": "canceled"},
            "Please change my plan to starter.",
            {},
        ),
        (
            "unpaid_refund",
            "Reject refund of an unpaid invoice",
            "policy",
            {"invoice.paid": False},
            "Please refund my latest invoice.",
            {},
        ),
    ]
    result = []
    for spec in specs:
        ident, title, category, initial, request, goal = spec[:6]
        profile = spec[6] if len(spec) > 6 else {"consent": True}
        state = base_state()
        for path, value in initial.items():
            set_path(state, path, value)
        expected = copy.deepcopy(state)
        for path, value in goal.items():
            set_path(expected, path, value)
        result.append(
            {
                "id": ident,
                "title": title,
                "category": category,
                "request": request,
                "user_profile": profile,
                "initial_state": state,
                "expected_state": expected,
            }
        )
    return result


def set_path(state, path, value):
    parts = path.split(".")
    for part in parts[:-1]:
        state = state[part]
    state[parts[-1]] = copy.deepcopy(value)


def differences(expected, actual, path=""):
    if isinstance(expected, dict) and isinstance(actual, dict):
        out = []
        for key in sorted(set(expected) | set(actual)):
            p = path + "." + key if path else key
            if key not in expected or key not in actual:
                out.append(
                    {
                        "path": p,
                        "expected": expected.get(key),
                        "actual": actual.get(key),
                    }
                )
            else:
                out.extend(differences(expected[key], actual[key], p))
        return out
    return (
        []
        if expected == actual
        else [{"path": path, "expected": expected, "actual": actual}]
    )


def pass_k(successes, n, k):
    if not isinstance(k, int) or isinstance(k, bool) or k < 1 or k > n:
        raise ValueError("k must be an integer between 1 and trial count")
    if successes < 0 or successes > n:
        raise ValueError("success count must be between 0 and trial count")
    return math.comb(successes, k) / math.comb(n, k) if successes >= k else 0.0


class Environment:
    """Owns mutable state and enforces tool policies; never sees a task goal."""

    def __init__(self, initial, code, intent):
        self.state = copy.deepcopy(initial)
        self.code = code
        self.intent = intent
        self.verified = False
        self.consent = False
        self.inspected = False
        self.violations = []
        self.trace = []

    def call(self, tool, arguments=None):
        args = arguments or {}
        try:
            result = self._call(tool, args)
        except (KeyError, TypeError, ValueError) as exc:
            result = {"error": "Invalid arguments: " + str(exc)}
        self.trace.append(
            {
                "role": "tool",
                "content": json.dumps(result),
                "tool": tool,
                "arguments": copy.deepcopy(args),
                "result": copy.deepcopy(result),
            }
        )
        return copy.deepcopy(result)

    def reject(self, reason):
        self.violations.append(reason)
        return {"error": reason}

    def _call(self, tool, args):
        if tool == "get_account":
            self.inspected = True
            return copy.deepcopy(self.state)
        if tool == "get_policy":
            return {"policy": POLICY}
        if tool == "verify_identity":
            self.verified = str(args.get("code", "")) == self.code
            return {"verified": self.verified}
        if tool not in (
            "change_plan",
            "cancel_subscription",
            "refund_invoice",
            "remove_member",
            "export_data",
        ):
            return {"error": "Unknown tool"}
        if not self.inspected:
            return self.reject("account_not_inspected")
        if not self.verified:
            return self.reject("identity_not_verified")
        if not self.consent:
            return self.reject("mutation_without_consent")
        if self.state["requester_role"] != "owner":
            return self.reject("owner_required")
        if tool != self.intent["tool"]:
            return self.reject("unrequested_mutation")
        s = self.state
        if tool == "change_plan":
            plan = args.get("plan")
            if plan != self.intent.get("plan"):
                return self.reject("unrequested_plan")
            if plan not in ("free", "starter", "pro"):
                return self.reject("unknown_plan")
            if s["status"] != "active":
                return self.reject("subscription_inactive")
            if s["balance_due"] > 0:
                return self.reject("unpaid_balance")
            if s["seats"] > {"free": 1, "starter": 5, "pro": 20}[plan]:
                return self.reject("seat_limit")
            s["plan"] = plan
        elif tool == "cancel_subscription":
            s["status"] = "canceled"
        elif tool == "refund_invoice":
            inv = s["invoice"]
            if not inv["paid"]:
                return self.reject("invoice_unpaid")
            if inv["age_days"] > 30:
                return self.reject("refund_window_expired")
            if inv["refunded"]:
                return self.reject("already_refunded")
            if args.get("amount") != inv["amount"]:
                return self.reject("incorrect_refund_amount")
            inv["refunded"] = True
        elif tool == "remove_member":
            member = args.get("member")
            if member != self.intent.get("member"):
                return self.reject("unrequested_member")
            if member == "owner":
                return self.reject("cannot_remove_owner")
            if member not in s["members"]:
                return self.reject("member_missing")
            s["members"].remove(member)
            s["seats"] -= 1
        elif tool == "export_data":
            s["export_requested"] = True
        return {"ok": True}


def parse_intent(request):
    request = request.lower()
    if "plan to " in request:
        return {
            "tool": "change_plan",
            "plan": request.split("plan to ")[1].split(".")[0].split()[0],
        }
    if "cancel" in request:
        return {"tool": "cancel_subscription"}
    if "refund" in request:
        return {"tool": "refund_invoice"}
    if "remove " in request:
        return {
            "tool": "remove_member",
            "member": request.split("remove ")[1].split()[0],
        }
    if "export" in request:
        return {"tool": "export_data"}
    return {"tool": "unknown"}


class ScriptedUser:
    """Seeded variations in phrasing and verification response; no expected state."""

    def __init__(self, request, seed, consent=True):
        self.consent = consent
        rng = random.Random(seed)
        self.code = str(rng.randint(100000, 999999))
        self.style = rng.choice(["plain", "verbose", "hesitant", "formatted"])
        self.request = rng.choice(["", "Hi! ", "Can you help? "]) + request

    def respond(self, message):
        if "confirm" in message.lower() or "proceed" in message.lower():
            return (
                "Yes, please proceed."
                if self.consent
                else "No, stop. I no longer want this action."
            )
        if "code" in message.lower():
            return {
                "plain": self.code,
                "verbose": "The verification code is " + self.code + ".",
                "hesitant": "Okay, I found it: " + self.code,
                "formatted": "Code: " + self.code[:3] + " " + self.code[3:],
            }[self.style]
        return "That is the request I need help with."


def scripted_agent(request, call, ask, aware, robust_auth=False):
    # Only public request + callable tools are passed. There is no task or goal input.
    import re

    intent = parse_intent(request)
    account = call("get_account", {})
    if aware:
        call("get_policy", {})
    reply = ask("Please provide your verification code.")
    code = "".join(re.findall(r"\d", reply)) if aware or robust_auth else reply.strip()
    auth = call("verify_identity", {"code": code})
    if aware and not auth.get("verified"):
        return "I could not verify your identity."
    tool = intent["tool"]
    if aware:
        if account["requester_role"] != "owner":
            return "Only an owner can perform this action."
        if tool == "change_plan":
            if (
                account["status"] != "active"
                or account["balance_due"] > 0
                or account["seats"]
                > {"free": 1, "starter": 5, "pro": 20}[intent["plan"]]
            ):
                return "The requested plan change is not eligible under the policy."
        if tool == "refund_invoice":
            inv = account["invoice"]
            if not inv["paid"] or inv["age_days"] > 30 or inv["refunded"]:
                return "This invoice is not eligible for a refund."
        if tool == "remove_member" and (
            intent["member"] == "owner" or intent["member"] not in account["members"]
        ):
            return "That member cannot be removed."
    confirmation = ask("Please confirm: should I proceed with your requested action?")
    if aware and not confirmation.lower().startswith("yes"):
        return "Understood. I have left your account unchanged."
    args = {k: v for k, v in intent.items() if k != "tool"}
    if tool == "refund_invoice":
        args["amount"] = account["invoice"]["amount"]
    result = call(tool, args)
    return (
        "The request is complete."
        if result.get("ok")
        else "I could not complete this request: "
        + result.get("error", "unknown error")
    )


def run_episode(task, agent_id, trial, seed, mode="scripted"):
    user = ScriptedUser(
        task["request"], seed, task.get("user_profile", {}).get("consent", True)
    )
    env = Environment(task["initial_state"], user.code, parse_intent(task["request"]))
    env.trace.append({"role": "user", "content": user.request})

    def ask(message):
        env.trace.append({"role": "assistant", "content": message})
        response = user.respond(message)
        if "confirm" in message.lower() or "proceed" in message.lower():
            env.consent = response.lower().startswith("yes")
        env.trace.append({"role": "user", "content": response})
        return response

    error = None
    telemetry = {}
    try:
        if mode == "live":
            from .live import live_agent

            response = live_agent(user.request, env.call, ask, telemetry=telemetry)
        else:
            response = scripted_agent(
                user.request,
                env.call,
                ask,
                agent_id == "policy-aware",
                agent_id == "auth-only",
            )
    except Exception as exc:
        error = type(exc).__name__ + ": " + str(exc)
        response = "Agent execution failed: " + error
    env.trace.append({"role": "assistant", "content": response})
    delta = differences(task["expected_state"], env.state)
    return {
        "task_id": task["id"],
        "agent_id": agent_id,
        "trial": trial,
        "seed": seed,
        "user_style": user.style,
        "success": not delta and not env.violations and error is None,
        "state_match": not delta,
        "policy_violations": env.violations,
        "trace": env.trace,
        "initial_state": copy.deepcopy(task["initial_state"]),
        "expected_state": copy.deepcopy(task["expected_state"]),
        "final_state": env.state,
        "differences": delta,
        "error": error,
        "telemetry": telemetry,
    }


def run(trials=8, seed=42, mode="scripted"):
    if trials < 8:
        raise ValueError("At least 8 trials are required for pass^8")
    suite = tasks()
    ids = (
        ["naive", "auth-only", "policy-aware"] if mode == "scripted" else ["live-model"]
    )
    episodes = [
        run_episode(task, agent, trial, seed + index * 1000 + trial, mode)
        for agent in ids
        for index, task in enumerate(suite)
        for trial in range(trials)
    ]
    agents = []
    for agent in ids:
        rows = [e for e in episodes if e["agent_id"] == agent]
        metrics = {
            str(k): sum(
                pass_k(
                    sum(e["success"] for e in rows if e["task_id"] == task["id"]),
                    trials,
                    k,
                )
                for task in suite
            )
            / len(suite)
            for k in (1, 2, 4, 8)
        }
        agents.append(
            {
                "id": agent,
                "name": {
                    "naive": "Naive scripted baseline",
                    "auth-only": "Authentication-only scripted ablation",
                    "policy-aware": "Policy-aware scripted baseline",
                    "live-model": "Live model",
                }[agent],
                "episodes": len(rows),
                "success_rate": sum(e["success"] for e in rows) / len(rows),
                "state_match_rate": sum(e["state_match"] for e in rows) / len(rows),
                "policy_compliance_rate": sum(not e["policy_violations"] for e in rows)
                / len(rows),
                "pass_k": metrics,
            }
        )
    return {
        "schema_version": 1,
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "mode": mode,
        "model_configuration": live_configuration() if mode == "live" else None,
        "seed": seed,
        "task_count": len(suite),
        "trials_per_task": trials,
        "agents": agents,
        "tasks": [{k: t[k] for k in ("id", "title", "category")} for t in suite],
        "episodes": episodes,
        "limitations": [
            "This is a tau-bench-inspired SaaS extension, not a reproduction of the original retail/airline results.",
            "Scripted baselines are deterministic programs; their results are not measurements of LLM ability.",
            "User variation covers phrasing, verification-code formatting, and a fixed consent withdrawal fixture, not unrestricted natural dialogue.",
            "Tools enforce policies and log rejected attempts; success requires both exact state match and zero recorded policy violations.",
            "Pass^k is estimated within each task then averaged equally across tasks. Trials share a scenario and use seeded variations; this is not a confidence interval.",
            "Policy-aware logic was written for this policy; perfect scripted scores demonstrate the fixture rather than generalization.",
            "Policy checks cover tool attempts, not every possible harmful statement in assistant text.",
        ],
    }


def live_configuration():
    import os

    return {
        "model": os.environ.get("TAULAB_MODEL"),
        "base_url": os.environ.get("TAULAB_BASE_URL", "https://api.openai.com/v1"),
        "max_tokens": 512,
        "max_turns": 12,
        "temperature": 0,
    }
