# PromptLab — agent instructions

The canonical agent brief for this repo is **[`../CLAUDE.md`](../CLAUDE.md)**. Read it.

It covers: what this repo is, which document owns which facts, build/run/test commands, the
prompts-vs-data-vs-code governance rule, the real quality gate per field, optimizer and
production stop rules, the Fly.io deployment state, and the Windows/flyctl gotchas.

Nothing is duplicated here deliberately. Until 2026-08-24 this file carried its own copy of that
material and had drifted badly out of step with the code — it described a 12-model roster (the
roster is 4), an accuracy gate on `sector_name` (it gates on Cohen's κ), `sub_sector` as a
categorical field (it is multi-valued), a Python venv in a sibling folder that no longer exists,
and a deploy procedure that assumed `entrypoint.sh` auto-starts the supervisor (it has not since
2026-08-20). Following those instructions would have caused real operational mistakes.

**So: one home for these facts, and this is not it.** If you are tempted to record a durable
project fact here, put it in `CLAUDE.md` instead.
