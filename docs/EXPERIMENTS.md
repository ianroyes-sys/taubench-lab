# Experiment protocol

## Status and research question

The local scripted experiment is a harness validation and domain extension. The original benchmark LLM run below is **planned, not executed**. This document specifies that future experiment before seeing its results; it is not an externally registered preregistration or a claim that development fixtures were held out.

Question: In synthetic SaaS support, does explicit policy verification improve successful completion without adding unacceptable latency, cost, or unnecessary refusals?

Hypothesis for a future LLM experiment: a policy-checking tool agent will improve the joint rate of correct outcome and valid policy trace compared with the same model and tools using a plain policy prompt. The scripted agents cannot test this hypothesis.

## A. Local development experiment

1. Freeze the fixture files and code revision before a reported run.
2. Use every included SaaS task, three scripted agent strategies, and eight seeded variations per task. Save the command, seed, task IDs, and individual outcomes.
3. Reset the complete database each episode. Never give the acting agent the expected final state or scoring labels.
4. Report outcome correctness, policy correctness, and their conjunction independently. Show per-task failures and unintended state changes.
5. Calculate pass^1, pass^2, pass^4, pass^8 per task using combinations, then average equally over tasks. Do not compute the metric from pooled successes across tasks. Require at least k observations for every included task; display unsupported values as unavailable.
6. Describe scores as reliability over the included scripted variations. Eight enumerated or seeded variations are not eight i.i.d. LLM conversations. Do not use an i.i.d. confidence interval for this demo.

The permissive baseline is deliberately incomplete; its gap from the scripted policy agent is evidence that the evaluator distinguishes specified behavior. It is not a competitive baseline or evidence of superiority to a language model.

## B. Original benchmark subset reproduction attempt

Scope: fixed retail test task IDs 0–9, eight trials each, tool-calling agent; no choosing tasks after viewing results. This produces 80 conversations and remains a subset study. It must not be compared directly with a paper-wide average or advertised as full reproduction.

The following commands match the inspected upstream CLI. They are a manual recipe and have not been executed here. Use an isolated environment because upstream dependencies have lower bounds rather than a historical lockfile.

```sh
git clone https://github.com/sierra-research/tau-bench tau-bench-upstream
cd tau-bench-upstream
git checkout 59a200c6d575d595120f1cb70fea53cef0632f6b
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python -m pip freeze > reproduction-environment.txt
```

Set `OPENAI_API_KEY` privately in the shell. Before any model run, verify access to the historical models and provider spending controls. Do not put credentials in a report or repository. Agent and simulated user both consume API usage, and the upstream agent's cost counter does not establish the full conversation bill.

```sh
python run.py \
  --env retail --task-split test \
  --task-ids 0 1 2 3 4 5 6 7 8 9 \
  --agent-strategy tool-calling \
  --model gpt-4o --model-provider openai \
  --user-model gpt-4-0613 --user-model-provider openai \
  --user-strategy llm --temperature 0 \
  --num-trials 8 --max-concurrency 1 --seed 10 \
  --log-dir results/retail-subset
```

This is a **historical-target command**, not a guarantee those models are available. Model aliases may have changed since 2024. Pin actual provider model versions if available. The inspected user code leaves temperature unspecified; explicitly enforce and record user temperature 1 before claiming method matching. Record any patch alongside its diff. Verify task revision and schema compatibility with the paper. If a historical model or data revision cannot be recovered, use an available model only under an **adapted replication** label and record the substitution.

Preflight a single task with one trial only after credentials and a spend limit are configured. Verify transcript, final-state reward, and both participants' token accounting. Stop on unresolved schema/provider errors. Then run the frozen subset with no prompt tuning against its results. Preserve failures, timeouts, and incomplete episodes; report completion counts and a sensitivity analysis for infrastructure failures instead of silently dropping them.

Artifacts: repository commit, dependency versions, provider/model IDs, task IDs, settings, start/end times, transcripts, rewards, per-task trial counts, total usage and cost, and outcome tables. A provider seed alone does not guarantee deterministic responses.

## C. SaaS LLM extension

Create a held-out task set with new accounts, amounts, policy boundary cases, and request compositions. Have another reviewer validate its expected states and consent requirements. Freeze it before either candidate is evaluated; current development fixtures are not held out.

Compare the same available LLM, user simulator, tools, action budget, and temperature in two conditions: plain policy prompt versus explicit policy verification. Permit equal development tuning, then freeze prompts. Run at least eight independently sampled conversations per task and condition. Keep the user simulator blind to agent internals and oracle state. Share task scenarios across conditions, but do not call paired seeds identical conversational randomness.

Primary outcome: per-task macro average of joint state-and-policy success. Secondary: state-only success, trace violations by category, pass^k, refusal errors, turns, latency, and measured API cost. Include a state-only scoring ablation to reveal errors an outcome-only evaluator misses. Use a task-level bootstrap for uncertainty after enough independently authored tasks exist; report the sample size and correlation limitations. Do not claim statistical significance from this small development suite.

Report absolute percentage-point differences and uncertainty, including negative results. Published benchmark trajectories, if reanalyzed, must be clearly attributed as **upstream recorded runs**, never fresh local LLM experiments.

## D. Completed reanalysis of author-recorded trajectories

`scripts/analyze_upstream.py` reads four published archives pinned to the inspected upstream commit and writes `results/upstream_reanalysis.json`. Run with `--source-dir /tmp/taubench-reference/historical_trajectories` for a local reference checkout, or `--download` to fetch the pinned files. The report records source identity, SHA-256 hashes, and task-level rewards.

| Archive | Tasks | Trials per task | Recorded episodes | pass^1 | pass^4 | pass^8 |
|---|---:|---:|---:|---:|---:|---:|
| gpt-4o-retail | 115 | 4 | 460 | 60.43% | 38.26% | unavailable |
| gpt-4o-airline | 50 | 4 | 200 | 42.00% | 20.00% | unavailable |
| sonnet-35-new-retail | 115 | 8 | 920 | 69.24% | 46.22% | 35.65% |
| sonnet-35-new-airline | 50 | 8 | 400 | 46.00% | 22.43% | 16.00% |

Total: **1,980 author-recorded episodes**. These are recomputations from the authors' saved reward labels; the script does not independently replay tools or regrade each reward. Archive model names are source labels, not newly verified provider versions. These archives and their later repository leaderboard are not automatically the original June 2024 paper table. The valid claim is **reproduced reliability metric calculations on published trajectories**, not reproduced the original model experiments. No new LLM calls were made for this analysis.
