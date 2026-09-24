# TauBench Lab

Research portfolio project inspired by Sierra's tau-bench (arXiv:2406.12045).

- Keep scripted control experiments visibly separate from live model results.
- Never describe this SaaS extension as a reproduction of the paper's published scores.
- Agents must never receive goal database states, expected actions, or evaluator labels.
- Validate exact database outcome and policy behavior independently.
- pass^k means all k trials succeed, not at least one; use the combinatorial estimator.
- Every reported number must come from a saved experiment artifact.
- Default execution must require no credentials or paid calls. Live runs must be explicit.
- Python standard library backend and dependency-free web dashboard; Python 3.9+.
- Run `python3 -m unittest discover -s tests -v` after backend changes.
- Run `python3 -m taulab run --output results/latest.json` to refresh the local experiment.
- Local dashboard: `python3 server.py`.
