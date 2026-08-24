# AGENTS.md

Agent instructions for this repo live in **[`CLAUDE.md`](CLAUDE.md)** — build/run commands,
governance rules, the quality gate, optimizer stop rules, and the Windows/flyctl gotchas.

Read that file. Nothing project-specific is duplicated here on purpose: two copies of the same
facts is how the previous version of these instructions ended up describing a gate, a model roster
and a deploy procedure that the code had already moved past.

Quick reference only:

```bash
npm install && npm run dev     # frontend → http://localhost:5173/promptlab/
npm run build                  # tsc -b && vite build
npm run lint                   # oxlint
npm test                       # vitest run

cd backend && pytest           # backend tests
```

Backend scripts run as packages from the repo root: `.venv/Scripts/python -m backend.scripts.<name>`.
