# Feature workflow setup — s002

Status: implementation of the requested setup; final human acceptance pending.
This is the bootstrap record for authoring the workflow, not a claim that the new workflow executed a product feature.

## Decisions

The user selected project-only installation, six agents, up to three developer/reviewer rounds per cycle, one correction cycle, and Sol/high for the correction tech lead. These specific choices resolve the conflicting general model table in the original request.

## Scope and acceptance

- AC-001: Six standalone project agent TOMLs use the exact role/model/effort assignments supplied by the user.
- AC-002: The main feature-workflow skill starts delegated work with tech-lead, interviews the human, records a task, and requires explicit approval of concrete spec/plan revisions before implementation.
- AC-003: Developer TDD, independent review, three-round limits, integrated QA, correction replanning and its approval, changed correction models, and final human intervention are explicit.
- AC-004: User-facing web features require actual browser QA with truthful blocked reporting if unavailable.
- AC-005: Task records include specifications, plans, state, review and verification; serialized ownership and snapshot identity preserve reliable handoffs and evidence.
- AC-006: Documentation, proportionate SOLID, scoped AGENTS.md maintenance, final checks and final human approval are explicit.
- AC-007: Skill validation, TOML parsing and independent scenario inspection are recorded; helper behavior is checked in an isolated repository.

Out of scope: product feature implementation, running the full six-role workflow on a feature, modifying global configuration, committing, publishing or deploying.

## Invocation preference

Follow-up user decision: feature-workflow should activate only when the user explicitly invokes it. Set its skill policy to `allow_implicit_invocation: false`; keep this scoped to feature-workflow.

## Architecture

Project agents live in `.codex/agents/`. Discoverable project skills live in `.agents/skills/`.
The main skill owns orchestration and references the task-record protocol. Two supporting skills own TDD and durable instruction maintenance. A read-only snapshot helper makes dirty working-tree identity reproducible, including untracked files. The lead owns stage transitions; workers receive one writer token at a time. Review and QA are independent evaluations. This is an instruction-driven workflow, not an automated state-machine service.
