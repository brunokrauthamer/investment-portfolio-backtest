# Task records and handoff protocol

## Files and ownership

Use `docs/tasks/<id>-<task-slug>/`, consistently plural `tasks`. Keep these five records:
- `spec.md`: revision, goal, scope/exclusions, assumptions, acceptance IDs and scenarios, constraints and human decisions.
- `plan.md`: revision, approved spec reference, explicit architecture/boundaries, alternatives, ordered slices/dependencies, verification strategy, risks and documentation impact.
- `state.json`: the coordination checkpoint, using the starting shape below.
- `review.md`: append a section per cycle/round and snapshot, verdict, findings, evidence and follow-up status. Preserve superseded findings.
- `verification.md`: TDD red/green/refactor evidence, QA criterion matrix, adverse cases, final checks, environments, limitations and evidence links, all tied to revisions.

Archive the prior contents before revising approved spec/plan files (e.g. `history/spec-s001.md` and `history/plan-p001.md`). Never treat mutable filenames as approval identifiers. The lead may number revisions (s001/p001); associate each with a SHA-256 content hash and record human approval against those exact contents.

## State ownership

The active lead owns transitions, counters, approvals, assignments, classification and `next_action`. A developer owns implementation status, snapshot and its verification references. The reviewer owns review status/findings and the QA agent owns acceptance results/QA status.

There is one state writer at a time. The lead grants a named writer token in the assignment, stops writing, waits for the worker's handoff, rereads the latest state, then resumes ownership. Only delegate one state-writing worker at a time. Workers preserve unrelated fields and increment `state_version`; write a temporary sibling and atomically replace `state.json`. Parallel read-only tasks return evidence to the lead instead of editing shared records. The same rule applies to shared Markdown files. Following interruption, the lead confirms the prior writer has stopped before reclaiming ownership.

Do not let every agent append to the interaction log concurrently. The main chat owns its exact user/assistant log entries under root guidance; workers return substantive messages for it to log when applicable.

## Starting shape

`null` means not established, never implicit success. Extra fields may record needed project facts without weakening these rules.

```json
{
  "schema_version": 1,
  "state_version": 1,
  "task_id": "001",
  "task_slug": "example-feature",
  "stage": "discovery",
  "spec_revision": null,
  "plan_revision": null,
  "code_revision": null,
  "baseline_revision": null,
  "model_policy": "initial",
  "correction_cycle": 0,
  "model_switch_reason": null,
  "review_rounds": {"initial": 0, "correction": 0},
  "limits": {"rounds_per_cycle": 3, "correction_cycles": 1},
  "state_writer": "tech-lead",
  "active_assignments": [],
  "implementation": {"status": "not_started", "evidence": []},
  "review": {"status": "not_started", "spec_revision": null, "plan_revision": null, "code_revision": null, "evidence": []},
  "qa": {"status": "not_started", "spec_revision": null, "plan_revision": null, "code_revision": null, "evidence": [], "browser": "not_assessed"},
  "acceptance_results": [],
  "open_findings": [],
  "attempts_without_progress": 0,
  "approvals": {"specification": null, "correction_plan": null, "final": null},
  "next_action": "interview the user"
}
```

Assignment objects: `id`, role/model/effort, criterion IDs, slice, allowed files, input revisions, writer ownership, deliverables and status. A worker handoff reports output snapshot, changed files, executed checks, remaining findings and recommended next action.

Acceptance result objects: criterion ID, pass/fail/blocked/not_run status, spec/plan/code revisions, expected/actual behavior and evidence. Finding objects: stable ID, source, severity, blocking boolean, criterion IDs, location, consequence, reproduction/evidence, status and resolution evidence. Keep resolved history in review/verification; never silently delete a finding.

Approval objects: human decision, exact spec/plan revisions and hashes (plus code snapshot for final approval), timestamp/timezone when reliable and conversation/task-record reference. Do not fabricate a person, timestamp or decision.

## Snapshot identity and evidence freshness

Before the first implementation, record Git HEAD and baseline worktree status so pre-existing user changes remain identifiable. Preserve their contents and ownership. Do not commit merely to obtain a snapshot.

Run `python <skill-dir>/scripts/snapshot.py --root <repository>` at handoff and before/after evaluation. It emits HEAD, a deterministic working-tree digest, and a list of path hashes (no contents). The snapshot covers tracked and nonignored untracked files, including tests, durable docs and config; it excludes `.git`, `docs/tasks/` and `docs/agent-log/` records, except that AGENTS.md files remain included because they are durable instructions. Save its output to task evidence when useful. Review untracked files too; a clean tracked diff is not a complete review.

A final evaluation's before/after snapshot must match. If implementation changes during review/QA, mark the result stale and evaluate the new snapshot. A current code snapshot does not transfer approval to a changed spec/plan. Reuse unaffected evidence only with explicit impact reasoning and traceable original results; record the current independent verdict on the current spec, plan and snapshot.

## Stages and gates

Normal path:
`discovery -> awaiting_spec_approval -> implementation -> review -> qa -> documentation -> final_verification -> awaiting_final_approval -> completed`.

- Review findings with rounds remaining: `review -> implementation`.
- Exhausted initial review or failed initial implementation QA: `correction_planning -> awaiting_correction_approval -> implementation` with correction models and counters.
- Correction review/QA failure after the allowed attempts: `needs_human_intervention`.
- Missing tools, dependencies, permissions or unresolved expectations: `blocked`, with the prior stage, concrete cause, owner and unblock action; never mark the criterion passed. Retain counters and resume from that stage when resolved.
- The correction lead can retain the approved spec if behavior remains unchanged, but the revised technical plan still needs human approval.
- Spec/acceptance/scope changes require a new explicit human decision and reapproval of the affected spec and plan. Preserve cycle/round history.
- Both initial and correction rounds are charged on dispatch of implementation/fix work, up to three each. Multiple bounded slices can belong to one declared pass. Integration is the active developer's responsibility under lead coordination.
- `attempts_without_progress` counts consecutive completed repair rounds with the same blocking findings and no new accepted criterion. New evidence that closes a blocking finding or passes a previously failing criterion resets it. Use it to prompt diagnosis; it never increases the round/cycle limits.
- Nonblocking findings can remain only with a recorded disposition and human acceptance where relevant. No unresolved blocking finding, failed/blocked required criterion, stale evaluation, or active assignment permits final approval.
- Final approval refers to exact revisions and snapshot. New implementation changes invalidate final approval. A completed task resumes only under a recorded new human request.

The lead audits these gates at every handoff; instruction-only coordination is not an automated state-machine enforcement service.
