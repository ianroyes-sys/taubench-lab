"""Summarize saved experiment evidence; never makes model requests."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def summarize(report):
    lines = ["# Saved experiment report", "", "Mode: " + report["mode"],
             "", "Model configuration: " + json.dumps(report.get("model_configuration")),
             "", "| Agent | Episodes | Joint success | State match | Policy compliance | pass^8 |",
             "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for agent in report["agents"]:
        lines.append("| {} | {} | {:.2%} | {:.2%} | {:.2%} | {:.2%} |".format(
            agent["name"], agent["episodes"], agent["success_rate"],
            agent["state_match_rate"], agent["policy_compliance_rate"], agent["pass_k"]["8"]))
    rows = report["episodes"]
    errors = sum(row.get("error") is not None for row in rows)
    lines += ["", "Execution errors: {} of {} episodes.".format(errors, len(rows))]
    timings = [seconds for row in rows for seconds in row.get("telemetry", {}).get("request_seconds", [])]
    usage = [item for row in rows for item in row.get("telemetry", {}).get("usage", [])]
    complete = [item for item in usage if isinstance(item, dict) and all(
        isinstance(item.get(key), int) and item[key] >= 0 for key in ("prompt_tokens", "completion_tokens"))]
    if timings:
        ordered = sorted(timings)
        lines += ["", "Measured model-request wall time (includes failed requests): mean {:.3f}s; p95 {:.3f}s; total {:.3f}s across {} requests.".format(
            sum(timings) / len(timings), ordered[math.ceil(.95 * len(timings)) - 1], sum(timings), len(timings)),
            "This measures endpoint request time, not full workflow latency."]
    else:
        lines += ["", "Model-request latency: not measured in this artifact."]
    if complete:
        lines += ["", "Reported tokens: {} input; {} output. Complete token records: {} of {} response records.".format(
            sum(item["prompt_tokens"] for item in complete), sum(item["completion_tokens"] for item in complete), len(complete), len(usage))]
    else:
        lines += ["", "Token usage: unavailable; do not interpret missing usage as zero."]
    lines += ["", "Dollar cost: unverified. Reconcile the run with provider billing, including failed requests, before claiming cost per task.",
              "", "## Limitations", ""]
    lines.extend("- " + item for item in report.get("limitations", []))
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artifact", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    raw = args.artifact.read_bytes()
    content = summarize(json.loads(raw))
    content += "\nArtifact: {}\n\nSHA-256: {}\n".format(args.artifact.name, hashlib.sha256(raw).hexdigest())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(content)
    print("Wrote " + str(args.output))
