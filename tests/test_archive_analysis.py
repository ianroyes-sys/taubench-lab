import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location(
    "archive", Path(__file__).resolve().parents[1] / "scripts/analyze_upstream.py"
)
archive = importlib.util.module_from_spec(spec)
spec.loader.exec_module(archive)


class ArchiveAnalysisTests(unittest.TestCase):
    def test_all_success_estimator_not_at_least_one(self):
        rows = [{"task_id": 0, "reward": r} for r in [1, 1, 0, 0]]
        result = archive.analyze(rows)
        self.assertEqual(result["pass_k"]["1"], 0.5)
        self.assertAlmostEqual(result["pass_k"]["2"], 1 / 6)
        self.assertEqual(result["pass_k"]["4"], 0)
        self.assertNotIn("8", result["pass_k"])

    def test_macro_average_with_unequal_trials(self):
        rows = [{"task_id": 0, "reward": 1}] + [{"task_id": 1, "reward": 0}] * 4
        self.assertEqual(archive.analyze(rows)["pass_k"], {"1": 0.5})

    def test_invalid_reward_and_empty(self):
        for rows in [[], [{"task_id": 0, "reward": 0.5}]]:
            with self.assertRaises(ValueError):
                archive.analyze(rows)

    def test_duplicate_trials_rejected(self):
        with self.assertRaises(ValueError):
            archive.analyze([{"task_id": 1, "trial": 0, "reward": 1}] * 2)

    def test_saved_metrics_recompute_from_bundled_rewards(self):
        import json

        path = Path(__file__).resolve().parents[1] / "results/upstream_reanalysis.json"
        for dataset in json.loads(path.read_text())["datasets"]:
            rows = [
                {"task_id": tid, "reward": reward}
                for tid, rewards in dataset["task_rewards"].items()
                for reward in rewards
            ]
            self.assertEqual(archive.analyze(rows)["pass_k"], dataset["pass_k"])
