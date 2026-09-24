import argparse
import json
import os
import tempfile
from pathlib import Path
from .benchmark import run


def main():
    parser = argparse.ArgumentParser(
        description="Run the tau-bench-inspired SaaS benchmark"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    command = sub.add_parser("run")
    command.add_argument("--output", default="results/latest.json")
    command.add_argument("--trials", type=int, default=8)
    command.add_argument("--seed", type=int, default=42)
    command.add_argument("--mode", choices=["scripted", "live"], default="scripted")
    args = parser.parse_args()
    if args.trials < 8:
        parser.error("--trials must be at least 8")
    if args.mode == "live" and not (
        os.environ.get("TAULAB_API_KEY") and os.environ.get("TAULAB_MODEL")
    ):
        parser.error(
            "Live mode requires TAULAB_API_KEY and TAULAB_MODEL; TAULAB_BASE_URL is optional"
        )
    report = run(args.trials, args.seed, args.mode)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w",
        dir=str(output.parent),
        prefix="." + output.name + ".",
        suffix=".tmp",
        delete=False,
    ) as handle:
        temp_path = handle.name
        json.dump(report, handle, indent=2)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temp_path, output)
    print("Wrote " + str(output))
    for agent in report["agents"]:
        print(
            "{}: {} episodes, success {:.1%}, policy compliance {:.1%}, pass^8 {:.1%}".format(
                agent["name"],
                agent["episodes"],
                agent["success_rate"],
                agent["policy_compliance_rate"],
                agent["pass_k"]["8"],
            )
        )
    errors = sum(e["error"] is not None for e in report["episodes"])
    if errors:
        print(
            "{} episodes failed with execution errors; inspect the report.".format(
                errors
            )
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
