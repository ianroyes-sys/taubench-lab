# Saved experiment report

Mode: scripted

Model configuration: null

| Agent | Episodes | Joint success | State match | Policy compliance | pass^8 |
| --- | ---: | ---: | ---: | ---: | ---: |
| Naive scripted baseline | 128 | 11.72% | 67.97% | 11.72% | 0.00% |
| Authentication-only scripted ablation | 128 | 43.75% | 100.00% | 43.75% | 43.75% |
| Policy-aware scripted baseline | 128 | 100.00% | 100.00% | 100.00% | 100.00% |

Execution errors: 0 of 384 episodes.

Model-request latency: not measured in this artifact.

Token usage: unavailable; do not interpret missing usage as zero.

Dollar cost: unverified. Reconcile the run with provider billing, including failed requests, before claiming cost per task.

## Limitations

- This is a tau-bench-inspired SaaS extension, not a reproduction of the original retail/airline results.
- Scripted baselines are deterministic programs; their results are not measurements of LLM ability.
- User variation covers phrasing, verification-code formatting, and a fixed consent withdrawal fixture, not unrestricted natural dialogue.
- Tools enforce policies and log rejected attempts; success requires both exact state match and zero recorded policy violations.
- Pass^k is estimated within each task then averaged equally across tasks. Trials share a scenario and use seeded variations; this is not a confidence interval.
- Policy-aware logic was written for this policy; perfect scripted scores demonstrate the fixture rather than generalization.
- Policy checks cover tool attempts, not every possible harmful statement in assistant text.

Artifact: latest.json

SHA-256: 788badfa96526558c15aa70e1bd5710484fa46c9faa03416794305132fb65136
