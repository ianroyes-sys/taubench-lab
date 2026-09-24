import copy
import inspect
import io
import json
import os
import math
import unittest
from unittest.mock import patch
from taulab.benchmark import (
    Environment,
    ScriptedUser,
    differences,
    parse_intent,
    pass_k,
    run,
    run_episode,
    scripted_agent,
    tasks,
)


class MetricsTests(unittest.TestCase):
    def test_exact_combinatorial_estimator(self):
        self.assertAlmostEqual(pass_k(6, 8, 4), 15 / 70)
        self.assertEqual(pass_k(6, 8, 8), 0)
        self.assertEqual(pass_k(8, 8, 8), 1)
        self.assertEqual(pass_k(0, 8, 1), 0)
        self.assertEqual(pass_k(6, 8, 1), 0.75)

    def test_invalid_k(self):
        for k in (0, -1, 9, 1.5, True):
            with self.assertRaises(ValueError):
                pass_k(6, 8, k)

    def test_state_comparison_checks_extraneous_mutations(self):
        self.assertTrue(
            differences({"plan": "pro"}, {"plan": "pro", "unexpected": True})
        )
        self.assertTrue(differences({"a": {"b": 1}}, {"a": {"b": 2}}))


class PolicyTests(unittest.TestCase):
    def env(self, ident):
        task = next(t for t in tasks() if t["id"] == ident)
        env = Environment(
            task["initial_state"], "123456", parse_intent(task["request"])
        )
        env.call("get_account")
        env.call("verify_identity", {"code": "123456"})
        env.consent = True
        return env

    def assert_rejected_unchanged(self, env, tool, args, reason):
        before = copy.deepcopy(env.state)
        self.assertEqual(env.call(tool, args), {"error": reason})
        self.assertEqual(env.state, before)
        self.assertIn(reason, env.violations)

    def test_negative_policies(self):
        cases = [
            ("seat_limit", "change_plan", {"plan": "starter"}, "seat_limit"),
            ("unpaid", "change_plan", {"plan": "starter"}, "unpaid_balance"),
            ("late_refund", "refund_invoice", {"amount": 120}, "refund_window_expired"),
            ("double_refund", "refund_invoice", {"amount": 120}, "already_refunded"),
            ("unpaid_refund", "refund_invoice", {"amount": 120}, "invoice_unpaid"),
            (
                "remove_owner",
                "remove_member",
                {"member": "owner"},
                "cannot_remove_owner",
            ),
            ("member_export", "export_data", {}, "owner_required"),
            (
                "canceled_change",
                "change_plan",
                {"plan": "starter"},
                "subscription_inactive",
            ),
        ]
        for ident, tool, args, reason in cases:
            with self.subTest(ident=ident):
                self.assert_rejected_unchanged(self.env(ident), tool, args, reason)

    def test_auth_and_scope(self):
        env = self.env("upgrade")
        env.verified = False
        self.assert_rejected_unchanged(
            env, "change_plan", {"plan": "pro"}, "identity_not_verified"
        )
        env.verified = True
        self.assert_rejected_unchanged(env, "export_data", {}, "unrequested_mutation")
        self.assert_rejected_unchanged(
            env, "change_plan", {"plan": "free"}, "unrequested_plan"
        )
        env.inspected = False
        self.assert_rejected_unchanged(
            env, "change_plan", {"plan": "pro"}, "account_not_inspected"
        )

    def test_consent_required(self):
        env = self.env("export")
        env.consent = False
        self.assert_rejected_unchanged(
            env, "export_data", {}, "mutation_without_consent"
        )

    def test_over_refund(self):
        self.assert_rejected_unchanged(
            self.env("refund"),
            "refund_invoice",
            {"amount": 121},
            "incorrect_refund_amount",
        )

    def test_cancellation_with_debt_is_allowed(self):
        env = self.env("cancel_unpaid")
        self.assertTrue(env.call("cancel_subscription", {})["ok"])
        self.assertEqual(env.state["balance_due"], 50)

    def test_read_results_are_detached(self):
        env = self.env("refund")
        result = env.call("get_account")
        result["invoice"]["amount"] = 999
        self.assertEqual(env.state["invoice"]["amount"], 120)


class IsolationTests(unittest.TestCase):
    def test_task_data_does_not_mutate(self):
        task = next(t for t in tasks() if t["id"] == "refund")
        before = copy.deepcopy(task)
        a = run_episode(task, "policy-aware", 0, 42)
        b = run_episode(task, "policy-aware", 0, 42)
        self.assertEqual(task, before)
        self.assertEqual(a, b)
        self.assertTrue(a["success"])

    def test_agent_interface_has_no_oracle(self):
        self.assertEqual(
            list(inspect.signature(scripted_agent).parameters),
            ["request", "call", "ask", "aware", "robust_auth"],
        )
        self.assertNotIn("expected_state", inspect.getsource(scripted_agent))
        self.assertNotIn("expected_state", inspect.getsource(Environment))

    def test_changing_oracle_cannot_change_behavior(self):
        task = tasks()[0]
        other = copy.deepcopy(task)
        other["expected_state"]["plan"] = "fictional"
        a = run_episode(task, "policy-aware", 0, 42)
        b = run_episode(other, "policy-aware", 0, 42)
        self.assertEqual(a["trace"], b["trace"])
        self.assertEqual(a["final_state"], b["final_state"])
        self.assertNotEqual(a["success"], b["success"])

    def test_rejected_attempt_is_failure_even_if_goal_matches(self):
        task = next(t for t in tasks() if t["id"] == "late_refund")
        row = run_episode(task, "naive", 0, 42)
        self.assertTrue(row["state_match"])
        self.assertFalse(row["success"])
        self.assertTrue(row["policy_violations"])

    def test_full_run_aggregation_and_variation(self):
        report = run()
        self.assertEqual(len(report["episodes"]), 16 * 8 * 3)
        self.assertGreater(len(set(e["user_style"] for e in report["episodes"])), 1)
        for agent in report["agents"]:
            rows = [e for e in report["episodes"] if e["agent_id"] == agent["id"]]
            self.assertEqual(
                agent["success_rate"], sum(e["success"] for e in rows) / len(rows)
            )
            self.assertAlmostEqual(agent["pass_k"]["1"], agent["success_rate"])
            self.assertGreaterEqual(agent["pass_k"]["1"], agent["pass_k"]["2"])
            self.assertGreaterEqual(agent["pass_k"]["2"], agent["pass_k"]["4"])
            self.assertGreaterEqual(agent["pass_k"]["4"], agent["pass_k"]["8"])

    def test_withdrawal_requires_no_mutation(self):
        task = next(t for t in tasks() if t["id"] == "withdraw_export")
        aware = run_episode(task, "policy-aware", 0, 42)
        ablation = run_episode(task, "auth-only", 0, 42)
        self.assertTrue(aware["success"])
        self.assertFalse(ablation["success"])
        self.assertIn("mutation_without_consent", ablation["policy_violations"])
        self.assertEqual(aware["initial_state"], aware["final_state"])
        self.assertEqual(ablation["initial_state"], ablation["final_state"])

    def test_live_adapter_records_config_usage_and_token_bound(self):
        from taulab.live import live_agent

        response = {
            "choices": [{"message": {"role": "assistant", "content": "Done"}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 2},
        }
        telemetry = {}
        with patch.dict(
            os.environ,
            {
                "TAULAB_API_KEY": "test-secret",
                "TAULAB_MODEL": "test-model",
                "TAULAB_BASE_URL": "https://example.invalid/v1",
            },
        ):
            with patch(
                "urllib.request.urlopen",
                return_value=io.BytesIO(json.dumps(response).encode()),
            ) as mocked:
                answer = live_agent("Hello", lambda *a: {}, lambda *a: "", telemetry)
        self.assertEqual(answer, "Done")
        payload = json.loads(mocked.call_args[0][0].data)
        self.assertEqual(payload["max_tokens"], 512)
        self.assertEqual(telemetry["usage"], [response["usage"]])
        self.assertEqual(telemetry["model"], "test-model")
        self.assertNotIn("test-secret", json.dumps(telemetry))

    def test_live_adapter_requires_credentials(self):
        from taulab.live import live_agent

        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(RuntimeError, "TAULAB_API_KEY"):
                live_agent("Hello", lambda *a: {}, lambda *a: "")

    def test_live_errors_fail_episode(self):
        with patch(
            "taulab.live.live_agent", side_effect=RuntimeError("endpoint unavailable")
        ):
            row = run_episode(tasks()[2], "live-model", 0, 42, "live")
        self.assertFalse(row["success"])
        self.assertIn("endpoint unavailable", row["error"])


if __name__ == "__main__":
    unittest.main()
