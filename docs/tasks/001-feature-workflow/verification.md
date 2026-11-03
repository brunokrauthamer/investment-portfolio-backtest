# Setup verification

Specification s001; plan p001; date 2026-11-02, America/Sao_Paulo.
This record verifies workflow authoring, not a full feature execution.

## Acceptance evidence

| Criterion | Result | Evidence |
| --- | --- | --- |
| AC-001 | Pass | All six TOMLs parsed with Python tomllib; exact role/model/effort assertions passed. |
| AC-002 | Pass | Independent discovery/approval scenario review and main-skill inspection. |
| AC-003 | Pass | Independent round-exhaustion, failed-pass, initial-QA, correction-QA and late-repair scenario review. |
| AC-004 | Pass | Browser QA requirement and blocked-tool routing inspected; no actual browser session claimed. |
| AC-005 | Pass | State example parsed; ownership/revision rules inspected; snapshot behavior checked in isolation. |
| AC-006 | Pass | Documentation destinations, proportional architecture, scoped guidance and final human gate inspected. |
| AC-007 | Pass | Required skill validators, config/metadata/link checks, helper checks and independent final review passed. |

## Checks actually executed

- Ran the bundled skill creator's unchanged `quick_validate.py` against feature-workflow, feature-tdd and maintain-agent-guidance. All three returned “Skill is valid!”.
- Parsed all six standalone TOMLs and asserted every requested role name, model and reasoning effort.
- Parsed UI YAML; checked description lengths and invocation prompts. Checked local Markdown references in all skills.
- Parsed the protocol's starting JSON and asserted three rounds per cycle and one correction cycle.
- Ran isolated Git-repository helper checks: deterministic identity; changed tracked files; inclusion of nonignored untracked files; exclusion of ordinary task/log records; inclusion of durable task AGENTS.md; deleted tracked files; root resolution from a nested directory. All passed.
- Ran `git diff --check`; no whitespace errors reported for tracked changes. New artifact formats were covered by the parsing and skill checks above.
- Ran an independent GPT-6.1 Sol / high scenario review and a follow-up inspection of final changes. The reviewer independently compared the actual and saved snapshot.

The default Python lacked validation dependencies. The bundled Python provided tomllib; PyYAML was installed only in a temporary validation directory and loaded for the skill validator. Earlier validation-launch failures were environment/invocation issues and were resolved before the successful checks. No project runtime dependency was added.

## Integrated artifact identity

See [snapshot.json](evidence/snapshot.json). The snapshot includes agent TOMLs, skills, helper and durable task guidance. Updating these setup records or the interaction log does not alter that snapshot.

## Limits and remaining human decision

No product feature was implemented, no six-role feature cycle was executed, and no browser QA was performed. The independent reviewer ran with the requested Sol/high settings; this does not establish runtime availability or automatic discovery of every configured role/model in a future session.

The workflow is instruction-driven. Its gates are enforced by the coordinating agents following the instructions; it is not an automated state-machine engine.

The task remains awaiting human acceptance of the setup. No commit, push, deployment or publication was performed.

## Explicit invocation update

On 2026-11-02, the user requested that feature-workflow activate only when explicitly invoked. Its `agents/openai.yaml` now sets `policy.allow_implicit_invocation: false`; the supporting skills were left unchanged. This final setting was inspected directly. No additional tests were requested or run for this one-field metadata change. The earlier independent review covers the preceding snapshot; see its follow-up note in [review.md](review.md).
