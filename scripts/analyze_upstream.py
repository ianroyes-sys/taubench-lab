"""Recalculate pass^k from authors' archived rewards, without model calls.

Usage: python3 scripts/analyze_upstream.py --source-dir /path/to/tau-bench/historical_trajectories
Or --download to fetch the four files from the pinned upstream commit.
"""

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
from math import comb
from pathlib import Path
from urllib.request import urlopen

COMMIT = "59a200c6d575d595120f1cb70fea53cef0632f6b"
FILES = [
    "gpt-4o-retail.json",
    "gpt-4o-airline.json",
    "sonnet-35-new-retail.json",
    "sonnet-35-new-airline.json",
]
HASHES = {
    "gpt-4o-retail.json": "df01707894836168ff0ec9616b0bf08f66c7e5afcf313e5fe4f7a2f5c2ec938b",
    "gpt-4o-airline.json": "e9e6c0297660c537f83d4fd9c476ce7a9a86ecd2784874b7bfc13be598e37bfa",
    "sonnet-35-new-retail.json": "0df526398e9d2720c32d340815cffb04fe8c4f8a61b1f4f84bf3bb558f760131",
    "sonnet-35-new-airline.json": "fe62fcd514b855b36f156dd4c3c7748597b392b006aff739b53337a9f3ba94d1",
}
ROOT = Path(__file__).resolve().parents[1]


def analyze(records):
    grouped = defaultdict(list)
    seen = set()
    for row in records:
        if "trial" in row:
            identity = (row["task_id"], row["trial"])
            if identity in seen:
                raise ValueError("Duplicate task/trial in archive")
            seen.add(identity)
        reward = row["reward"]
        if reward not in (0, 1):
            raise ValueError("Expected binary archived reward")
        grouped[str(row["task_id"])].append(int(reward))
    if not grouped:
        raise ValueError("No archived tasks")
    minimum = min(map(len, grouped.values()))
    estimates = {}
    for k in (1, 2, 4, 8):
        if k <= minimum:
            estimates[str(k)] = sum(
                comb(sum(rs), k) / comb(len(rs), k) for rs in grouped.values()
            ) / len(grouped)
    return {
        "episodes": len(records),
        "tasks": len(grouped),
        "trials_min": minimum,
        "trials_max": max(map(len, grouped.values())),
        "pass_k": estimates,
        "task_rewards": dict(sorted(grouped.items(), key=lambda pair: int(pair[0]))),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--source-dir", type=Path)
    source.add_argument("--download", action="store_true")
    parser.add_argument(
        "--output", type=Path, default=ROOT / "results/upstream_reanalysis.json"
    )
    args = parser.parse_args()
    report = {
        "kind": "archived_reward_reanalysis",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "upstream_commit": COMMIT,
        "datasets": [],
        "limitations": [
            "Authors' archived rewards; no new model inference or independent trajectory regrading.",
            "Archives may differ from the paper's original evaluation revision; not an exact table replication.",
            "No pass^k estimate when fewer than k trials exist for any task.",
            "Model archives are not a controlled head-to-head experiment.",
        ],
    }
    for name in FILES:
        url = (
            "https://raw.githubusercontent.com/sierra-research/tau-bench/%s/historical_trajectories/%s"
            % (COMMIT, name)
        )
        if args.download:
            with urlopen(url, timeout=60) as response:
                raw = response.read()
        else:
            raw = (args.source_dir / name).read_bytes()
        if hashlib.sha256(raw).hexdigest() != HASHES[name]:
            raise ValueError(
                "Source hash mismatch for "
                + name
                + "; refusing to attribute changed data to the authors"
            )
        result = analyze(json.loads(raw))
        result.update(
            {"file": name, "source_url": url, "sha256": hashlib.sha256(raw).hexdigest()}
        )
        report["datasets"].append(result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n")
    for item in report["datasets"]:
        print(item["file"], item["episodes"], "episodes", item["pass_k"])


if __name__ == "__main__":
    main()
