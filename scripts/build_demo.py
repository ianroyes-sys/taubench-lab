#!/usr/bin/env python3
"""Export the committed, credential-free research snapshot as a static site."""
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "dist"
REPOSITORY = "https://github.com/ianroyes-sys/taubench-lab"


def main():
    # Export only the two reviewed artifacts, never live results or arbitrary files.
    artifacts = ("latest.json", "upstream_reanalysis.json")
    for name in artifacts:
        data = json.loads((ROOT / "results" / name).read_text())
        if name == "latest.json" and data.get("mode") != "scripted":
            raise ValueError("The public demo only accepts scripted baseline results")
    DEST.mkdir(exist_ok=True)
    (DEST / "data").mkdir(exist_ok=True)
    for name in ("app.js", "styles.css"):
        shutil.copyfile(ROOT / "web" / name, DEST / name)
    html = (ROOT / "web" / "index.html").read_text()
    html = html.replace('data-mode="local"', 'data-mode="snapshot"')
    html = html.replace("RESEARCH WORKSPACE", "PUBLIC RESEARCH SNAPSHOT")
    html = html.replace(
        "SCRIPTED BASELINES</span>",
        'SCRIPTED BASELINES</span><span class="snapshot-label">SAVED EXPERIMENT · INTERACTIVE SNAPSHOT</span>',
    )
    html, count = re.subn(
        r'<button id="run".*?</button>',
        '<a class="source-link" href="'
        + REPOSITORY
        + '#run-in-one-minute">View code & run locally ↗</a>'
        '<p class="snapshot-note">Explore saved results below. This public demo does not execute agents or make model calls.</p>',
        html,
        flags=re.DOTALL,
    )
    if count != 1:
        raise ValueError("Expected exactly one local benchmark run button")
    (DEST / "index.html").write_text(html)
    for name in artifacts:
        shutil.copyfile(ROOT / "results" / name, DEST / "data" / name)
    (DEST / ".nojekyll").write_text("")
    print(
        "Built dist/: interactive saved results, relative paths, no backend required."
    )


if __name__ == "__main__":
    main()
