---
name: maintain-agent-guidance
description: Update small, scoped AGENTS.md instructions when feature work changes durable commands, paths, boundaries or practices that future agents need.
---

# Maintain agent guidance

Ask: does this discovery change how a future agent should work in this area? If not, use product documentation, architecture, an ADR or the task record.

Inspect the integrated diff and affected commands, paths and boundaries. Update only durable guidance at the smallest appropriate directory scope. Keep the root AGENTS.md short, normally a few dozen lines; keep essential instructions and move local detail into relevant subdirectories rather than truncating it.

Remove or replace obsolete guidance. Verify referenced files, links, examples and commands against the project. Give instruction changes to the reviewer alongside the code. If a modified rule must govern the current execution, explicitly reread it before proceeding; do not assume it reloads automatically.

Do not generalize an isolated failure into a universal prohibition. Do not lower quality requirements to finish a task. Changes to autonomy, authorization or acceptance criteria require the appropriate human decision, not an incidental instruction edit. Preserve privacy and the root interaction-log requirement.
