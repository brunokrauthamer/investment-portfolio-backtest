---
name: feature-workflow
description: Develop a new project feature through a tech lead interview, human-approved specification and plan, delegated TDD, independent review and QA, one bounded correction cycle, and final human approval. Resume an existing feature from its task records.
---

# Feature workflow

Use the six project agents in `.codex/agents/`. Read [the task-record protocol](references/task-records.md) before creating or resuming a task. Do not turn a setup, status, or explanation request into feature execution.

## Coordinator and delegation

Start every invocation with `tech-lead` (GPT-6.1 Terra / xhigh). For an existing correction task, this opening handoff reads state and routes ongoing work to `tech-lead-correction`; it does not reset counters or reapprove anything. The correction lead is GPT-6.1 Sol / high. Only one lead is active at a time.

The main chat relays the lead's interview questions and approval requests to the human, then sends exact answers back to the lead. The lead owns discovery, the plan, delegation, integration, evidence audit, and the final report. The main chat must not silently replace that role.

Spawn by custom agent name when the available tool supports it. Otherwise read the role's TOML and spawn a fresh agent with its exact `developer_instructions`, explicit `model`, and explicit `model_reasoning_effort`; use no inherited conversation when required for overrides. Include the task path, relevant decisions and repository guidance in the assignment. If the tool cannot honor the requested model/effort, report the limitation and request a decision; do not silently substitute. Configuration alone is not evidence that an agent actually ran.

Each assignment carries the approved spec/plan revisions, criterion IDs, bounded files or behavior, input snapshot, deliverables, writer ownership, and return conditions. Wait for dependent work. Respect available concurrency; use sequential handoffs by default. Only the active lead dispatches workers. Review and QA use fresh agents independent of the author, with primary specifications and executable artifacts, not an author's claimed verdict.

## 1. Discover and obtain approval

The lead interviews the user about outcomes, blind spots, adverse cases, constraints and exclusions, using the existing architecture and code. Ask focused questions only while missing answers affect behavior or design.

Create `docs/tasks/<id>-<task-slug>/` with `spec.md`, `plan.md`, `state.json`, `verification.md`, and `review.md`. Use the task name in the directory and the next available ID. Records must distinguish proposed decisions, executed work and observed evidence.

Specify:
- Stable acceptance IDs (AC-001, ...), observable outcomes, adverse cases and out-of-scope behavior.
- Architecture: component responsibilities, dependencies, interfaces/data flow, affected boundaries and risks. Apply SOLID in proportion to the problem; justify new abstractions.
- Ordered implementation slices, test strategy, integrated run instructions, browser scenarios for user-facing web behavior, documentation and final checks.

Show the complete, concrete spec and plan with revision identifiers and links. Set `awaiting_spec_approval` and wait for explicit human approval of both revisions before implementation. Approval of a previous feature or a general workflow is not approval of this feature's design. Record the decision and exact approved revisions.

## 2. Initial implementation and review

Use `developer` (GPT-6 Luna / max), with the sibling [feature-tdd skill](../feature-tdd/SKILL.md). Implement bounded slices with tests first, then integrate the planned change. The developer updates affected documentation, records TDD evidence in `verification.md`, and updates its assigned state fields before returning the writer token.

A round consists of one implementation/fix pass and the following independent integrated review, across the feature, not per slice. Increment the round when dispatching that pass; a failed or abandoned pass consumes its round. Allow at most three rounds in this initial cycle. If a pass fails before producing a reviewable snapshot, record its failure and let the lead route an implementation retry within the remaining budget; at exhaustion use correction planning initially and human intervention in correction. Environment/tool failures remain blocked pending resolution; they do not justify a model switch.

Use `reviewer` (GPT-6.1 Sol / high). Supply approved spec, plan/architecture and the integrated snapshot. The reviewer independently checks the diff, behavior risks, tests, architecture, documentation and instruction changes; writes a dated entry in `review.md`; and updates the assigned review/findings fields in `state.json`. Findings need ID, severity, location, consequence, evidence and related criteria. The reviewer does not edit the implementation or redefine expectations.

The lead routes actionable findings to the developer while rounds remain. For each confirmed implementation defect found during implementation, review, or QA, the active developer must follow the feature-tdd skill: write a specific regression test that reproduces the issue and observe it fail before fixing it, then record the passing result. This also applies to the correction developer and to late repairs. Disputed findings require evidence or a recorded decision; they cannot disappear because the author disagrees. A fix requires independent re-review. If review passes, move to QA immediately; do not spend unused rounds. If round three still has blocking findings, obtain QA's available independent assessment, marked blocked where execution is unsafe or impossible, then enter correction planning. Never call that a pass.

## 3. Independent integrated QA

Use `qa` (GPT-6 Luna / max). Verify every approved criterion on the integrated snapshot, plus adverse cases and relevant regressions. Record expected/actual behavior, reproduction, environment and evidence in `verification.md`, and update assigned acceptance/QA fields.

For web features with user-facing behavior, QA must exercise the integrated feature in a browser through available browser tooling. Unit tests, source inspection, HTTP calls, mock-only flows, and developer screenshots do not replace this. Use the applicable browser/computer-use instructions. Record actual browser actions and observed results. If QA cannot access browser tools, return a blocked result for the lead to arrange tool access or relay QA-directed browser execution with explicit attribution. Never invent a browser pass.

QA does not change code or redefine criteria. Distinguish implementation/architecture failures from environment/tool blockers and spec ambiguities. Resolve tool blockers without charging a correction cycle; bring ambiguous expectations to the human. Code changes after review require renewed review and affected QA on the new snapshot.

## 4. One correction cycle

Trigger correction when initial review exhausts three rounds, or initial QA finds an implementation/architecture defect. Record the evidence, `correction_cycle = 1`, `model_policy = "correction"`, and `model_switch_reason`. Switch to `tech-lead-correction` and `developer-correction` (GPT-6.1 Terra / medium); reviewer and QA keep their original assignments.

The correction lead diagnoses the failure, revises architecture/technical planning as needed, and presents a concrete revised plan for human approval before correction code is written. Spec changes also require explicit approval. Preserve old revisions and evidence. Within the approved scope, keep valid criteria; never reduce expectations to obtain a pass.

Restart implementation/review with the correction developer for at most three rounds, then independent QA. Keep the original counters and use a separate correction round counter. There is no automatic second correction cycle. If correction review exhausts its limit or correction QA still finds implementation/architecture problems, set `needs_human_intervention`, summarize reproductions, evidence, attempted fixes and options, and wait for the human. Do not reset counters by renaming the task or agent. Human-authorized further work requires a recorded new decision.

## 5. Documentation, final checks, and approval

The active developer owns affected documentation. Use the sibling [maintain-agent-guidance skill](../maintain-agent-guidance/SKILL.md) for durable instruction discoveries. No separate records or documentation agent is required.

Update only relevant destinations: README/development guide for usage, `docs/architecture/` for current design, `docs/decisions/` for significant decisions and consequences, release notes for user-visible changes. Task files hold feature-specific evidence; Git holds the complete diff/authorship.

The active lead audits all approved criteria, unresolved findings, review/QA freshness, documentation, and actual final checks. Record commands, outcomes, limitations and artifact references. Changes to application code, tests, configuration or durable documentation after evaluation create a new snapshot; re-review affected changes and rerun affected checks/QA. Records alone do not invalidate a code snapshot. Late code, test, configuration or documentation repairs use the same remaining development-round budget; they do not create free extra rounds. If another repair pass is needed after round three, route the initial cycle to correction planning or the correction cycle to human intervention. Review-only and QA-only reruns on unchanged inputs do not consume a development round.

Only when all required checks and independent evaluations pass on the current snapshot, no blocking findings remain, and no assignments are active, set `awaiting_final_approval`. Present the result, evidence, risks and any explicitly accepted nonblocking items for human review. Wait for explicit final human approval of that spec and snapshot; then record it and set `completed`. Delivery approval does not authorize a commit, push, merge, deployment, publication, or other external action.
