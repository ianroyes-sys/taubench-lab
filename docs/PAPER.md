# Paper notes and implementation map

**Status:** TauBenchLab is an independent SaaS evaluation extension inspired by τ-bench. Scripted local runs are software demonstrations. They do not reproduce the paper's LLM results.

## What the paper asks

Yao, Shinn, Razavi, and Narasimhan (2024) study whether agents reliably complete customer-service work through conversations and tools while following policies. Retail and airline scenarios pair a database, tool functions, policy text, and hidden user instructions. An LLM simulates the customer.

Success combines the final database outcome with any required answer strings. This can miss violations such as taking an action without confirmation. The paper defines pass^k as the probability of success on **all** k independent trials of a task, averaged across tasks; pass@k instead needs only one success.

For n trials and c successes, estimate pass^k with `C(c,k) / C(n,k)`; use zero when c < k. The main experiments use at least three trials, a 30-action limit, agent temperature 0, and user temperature 1. The original user model is `gpt-4-0613`.

Read the [abstract/introduction and sections 3–5](https://arxiv.org/html/2406.12045v1) before interpreting results.

## Implementation checklist

| Component | Our engineering work | Verification evidence |
|---|---|---|
| Domain | Synthetic SaaS subscriptions and support rules | Inspect task fixtures and documented policy |
| Isolation | Fresh database per episode; oracle hidden from acting agent | Tests for reset behavior and agent inputs |
| Tools | Observable reads and auditable writes | Tool traces and state diffs |
| User variation | Seeded scripted variations | Repeat a run with the same seed |
| Outcome | Compare the complete final state with an independent expected state | Tests for missing and unintended mutations |
| Policy extension | Score intermediate actions separately from outcome | Cases where state is right but consent is absent |
| Reliability | Per-task combination estimator, then macro average | Hand-check all-success, zero-success, mixed-success cases |
| Review | Inspect individual failures before describing improvements | Saved JSON traces and report |

Scripted variations give a finite scenario coverage score. They are not independent samples from an LLM conversation distribution. A successful scripted policy agent shows the fixture is solvable and the harness works; it does not establish an AI improvement.

## Inspected upstream code

Repository: [sierra-research/tau-bench](https://github.com/sierra-research/tau-bench). Inspected commit: `59a200c6d575d595120f1cb70fea53cef0632f6b` on 2026-09-24. This is the inspected legacy repository revision, **not a claim that it is the original paper's experiment revision**.

- [run.py CLI](https://github.com/sierra-research/tau-bench/blob/59a200c6d575d595120f1cb70fea53cef0632f6b/run.py): task selection, trial count, model, temperature, and seed flags.
- [Environment scoring](https://github.com/sierra-research/tau-bench/blob/59a200c6d575d595120f1cb70fea53cef0632f6b/tau_bench/envs/base.py): replays reference actions from a reset database; compares state hashes; checks required response substrings.
- [Tool agent](https://github.com/sierra-research/tau-bench/blob/59a200c6d575d595120f1cb70fea53cef0632f6b/tau_bench/agents/tool_calling_agent.py): defaults to 30 steps and temperature 0.
- [User simulator](https://github.com/sierra-research/tau-bench/blob/59a200c6d575d595120f1cb70fea53cef0632f6b/tau_bench/envs/user.py): ordinary completion omits an explicit temperature; verify provider behavior before a paper-matched run.

The current upstream README labels the legacy tasks outdated and directs current benchmark users to its successor repository. We retain the legacy reference to study the selected 2024 paper. Results on newer task versions need separate labels.
