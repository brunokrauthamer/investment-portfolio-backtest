---
name: simple-feature-workflow
description: Implement a project feature through an approved spec and plan, one independent review, at most one post-review fix, and independent QA. Use when the user requests the simplified feature workflow; distinguish it from feature-workflow.
---

# Simple feature workflow

Use this workflow when the user invokes it or requests this simplified process. Do not start feature implementation for a request that only asks for an explanation or status. Keep the existing feature-workflow and its tasks independent; never reinterpret an existing task under this workflow without a user decision.

## Coordination and roles

The main chat starts and relays questions and decisions to `simple-tech-lead`, who coordinates the work and reports back. Use these separate role configurations in `.codex/agents/`:

| Role | Model | Reasoning effort |
| --- | --- | --- |
| simple-tech-lead | gpt-6.1-terra | high |
| simple-developer | gpt-6-luna | max |
| simple-reviewer | gpt-6.1-terra | high |
| simple-qa | gpt-6-luna | max |

Spawn by the custom role name when supported. Otherwise read the corresponding TOML and spawn a fresh agent with its exact instructions, model and effort, without inherited conversation when needed for overrides. Include applicable repository instructions, task context, approved spec and plan, and owned scope in assignments. If the tool cannot honor the model and effort, report the limitation and ask the user how to proceed; do not silently substitute. Only the lead dispatches workers. Use independent reviewer and QA agents, not the developer. Work sequentially and wait for each handoff.

## Workflow

1. **Spec and plan:** The lead examines the relevant code, asks focused questions where decisions affect behavior, and prepares a concrete specification and implementation plan with observable acceptance criteria, scope, architecture and checks. Agree on financial and data conventions before implementing behavior that depends on them. Present both to the user; incorporate requested adjustments and wait for explicit approval before development.
2. **Develop:** The developer implements the approved plan, runs appropriate tests, and updates affected documentation. Use meaningful test-first red/green evidence for new behavior and confirmed defects when executable tests apply. Report changes, checks, limitations and a reviewable snapshot.
3. **Review:** The reviewer independently examines the integrated result against the approved spec and plan, including tests and risks, and reports actionable findings with evidence. The lead routes confirmed actionable findings to the developer for **at most one** post-review code-fix pass. The developer runs affected checks and hands off the result. There is no second review or further automatic code-fix pass; proceed directly to QA whether or not findings remain, and give QA the findings and fix results. If review has no actionable findings, proceed directly to QA.
4. **QA:** QA independently tests the resulting integrated snapshot against the acceptance criteria and relevant regressions. For user-facing web behavior, exercise it in a browser when available; report missing access as blocked, not as a pass. Report expected and actual outcomes, evidence, remaining review findings and blockers. QA does not fix code.
5. **Report and stop:** The lead reports the outcome and any problems or limitations to the user. If a problem remains or a required check is blocked, stop and let the user decide what to do; do not automatically retry, create a correction cycle, switch models, or claim success. If checks pass, report completion. Do not require a separate final approval merely to complete the task. Commit, push, merge and deploy require their own authorization.

If implementation or review cannot produce a usable handoff, or a required decision is ambiguous, report the issue and wait for the user's decision rather than silently retrying. Record factual evidence; never invent a test result or approval. Changes in scope or acceptance criteria require user agreement. Preserve existing user changes.

## Records

Create a distinct `docs/tasks/<id>-<slug>/` using the next available ID. Record the workflow name, spec and plan, approval, changes, review findings, the single fix pass if used, QA results, and final status. Preserve observations and decisions for resumption; distinguish passed, failed and blocked checks. Only one agent writes shared task records at a time. Follow applicable `AGENTS.md` instructions, including the main chat's interaction log. Do not adopt the existing feature-workflow's retry limits, correction cycle, or final approval gate for this workflow.
