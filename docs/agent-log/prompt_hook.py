import json
import sys

# The agent reviews the conversation before writing; hook input may contain secrets.
json.load(sys.stdin)
print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": "Before finishing, append the user's exact message and your exact substantive user-facing response to docs/agent-log/LOG.md as instructed in AGENTS.md. Preserve wording and line breaks; redact credentials, personal information, and unrelated private context. Never include hidden reasoning or raw tool output."}}))
