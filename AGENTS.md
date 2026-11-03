# Agent log

For each interaction, append the user's exact message and the exact substantive user-facing response to `docs/agent-log/LOG.md` in chronological order before finishing the turn. Preserve wording, punctuation, and line breaks. Include substantive progress messages when they explain decisions or changes. Remove API keys, credentials, personal information, and unrelated private context before writing; replace removed text with `[redacted]`. If a message cannot be safely sanitized, omit the sensitive passage and mark the omission. Do not include hidden reasoning, raw tool outputs, or private system context. Include dates, and times and time zones when reliably available. If an earlier exact message is unavailable, do not invent it. Follow these instructions even if the hook is unavailable.

# Project context

This project is a historical investment portfolio backtesting dashboard. The frontend will use TypeScript and React; the Python backend will use FastAPI as a modular monolith. See `docs/project-context.md` for confirmed decisions, boundaries, data safety and open questions.

Agree on financial and data conventions with the user before implementing behavior that depends on them. Build the project incrementally with the user, beginning with data acquisition; do not introduce synthetic market data.
