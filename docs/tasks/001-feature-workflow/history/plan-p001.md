# Feature workflow setup — p001

Specification: s001. The user authorized creation and answered scope/cycle questions; this bootstrap does not retroactively claim a separate feature-plan approval.

1. Verify official custom-agent TOML and skill discovery formats.
2. Create the six project agents with bounded role instructions and exact model settings.
3. Create feature-workflow with the task-record protocol, plus feature-tdd and maintain-agent-guidance.
4. Add a read-only snapshot helper to identify integrated versions without requiring commits.
5. Validate skills, parse configuration and inspect references; verify snapshot behavior in isolation.
6. Independently inspect realistic workflow scenarios and address supported findings.
7. Record results, limitations and the final reviewable files, awaiting human acceptance.

## Boundaries and risks

No global agent/model settings change. No product code is added. Actual model access and custom-agent discovery are runtime concerns; static validation cannot prove them. The main skill defines explicit-model dispatch when custom-role spawning is unavailable. Missing browser tools block QA rather than producing a pass. Task-state gate compliance is the lead's responsibility.

Official references:
- [Subagents](https://learn.chatgpt.com/docs/agent-configuration/subagents)
- [Build skills](https://learn.chatgpt.com/docs/build-skills)
- [Model IDs and reasoning levels](https://developers.openai.com/api/docs/models)
