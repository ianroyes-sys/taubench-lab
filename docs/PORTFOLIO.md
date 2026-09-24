# Portfolio and interview guide

## Project positioning

**TauBenchLab — evaluating SaaS support-agent reliability**

An independent Python evaluation project inspired by the 2024 τ-bench paper. It models subscription support workflows and tests whether an agent both reaches the expected database state and follows policy along the way. Its first deliverable is a reproducible scripted harness, with a defined protocol for future LLM experiments.

Relevant startup work: support automation, agent quality checks before release, debugging failed tool actions, and evaluating the tradeoff between reliability and operating cost. This is an interview artifact, not evidence of production savings or customer outcomes.

## Resume bullets you can use after reviewing the implementation

- Built a Python evaluation harness for synthetic SaaS support workflows, with isolated database state, auditable tool traces, and separate outcome and policy checks.
- Implemented τ-bench's pass^k estimator and extended evaluation with intermediate policy checks to expose failures that final-state scoring can miss.
- Evaluated three scripted support-agent strategies across 16 synthetic SaaS scenarios and 384 episodes, distinguishing final-state correctness from policy-compliant completion.
- Recomputed pass^k reliability metrics from 1,980 published τ-bench episodes, preserving source revision, file hashes, and task-level reward evidence; distinguished author-recorded outcomes from new local experiments.

Add task counts, trial counts, test counts, and percentages **only from the final committed report**, identifying them as synthetic scripted results. Read the code and rerun the project before putting it on your resume; be ready to explain what you personally understand and how AI assistance was used.

## Templates reserved for future measured LLM work

- Evaluated [model/version] on [N] frozen τ-retail tasks over [n] trials each; recorded [X]% pass^1 and [Y]% pass^4, with [cost] measured total API usage.
- On [N] independently authored held-out SaaS tasks, changed joint state-and-policy success from [A]% to [B]% using [specific intervention], with [interval] uncertainty and [latency/cost] impact.

Do not fill these placeholders from scripted scores or published author trajectories. Do not say “reproduced the paper,” “improved GPT-4,” or “reduced startup costs” without the corresponding experiment and evidence.

## Five-minute walkthrough

1. **Problem:** A support agent can sound convincing yet apply a wrong change or act before permission.
2. **Paper:** Explain a tool-agent-user episode, state-based scoring, and the distinction between pass^k and pass@k.
3. **Implementation:** Open one task fixture, the tool boundary, the independent oracle, and its saved trace.
4. **Extension:** Demonstrate a case with the correct final state but an invalid action sequence; explain why both scores are needed.
5. **Limits:** State that the initial agents and users are scripted, the dataset is synthetic and used during development, and LLM replication remains pending.

## Interview questions to prepare

- Why use `C(c,k)/C(n,k)`? It averages success over all k-element subsets of observed trials. Taking the pooled success rate to the kth power ignores task difficulty; multiplying success rates also gives a different finite-sample estimate.
- Why can a correct state still be wrong? An action may have occurred before consent, or an invalid intermediate action may have been undone.
- Does 100% prove reliability? Only within the tested fixture set and acting strategy. Independent tasks and sampled conversations are needed to study generalization.
- How do you avoid oracle leakage? Keep expected states and hidden scenario instructions outside the agent's observation boundary, and test that separation.
- What would ship at a startup? A versioned evaluation suite in release checks, failure traces reviewers can inspect, and live monitoring informed by real support cases.
- What is the next experiment? Freeze held-out tasks, compare the same LLM with and without explicit policy verification, and measure both quality and cost.

## Publication checklist

Keep the README, local run command, tests, report, methodology, limitations, and source attribution together. Add a short screen recording showing one failure and the corresponding trace. Remove secrets and personal customer data. Publish only when the repository and claims have been reviewed. GitHub publication and any resume/profile updates are separate actions from this local build.
