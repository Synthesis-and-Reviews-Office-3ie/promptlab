# PromptLab — agent instructions

**This file is the canonical agent brief.** `AGENTS.md` and `.github/copilot-instructions.md` are
thin pointers to it — do not let them accumulate their own copy of these facts again (that drift is
exactly what made them wrong).

Every constant below was verified against the code on **2026-08-24**. When you change one of these
behaviours in code, update this file in the same commit or delete the claim.

## What this repo is

`github.com/Synthesis-and-Reviews-Office-3ie/promptlab` (moved from `lsempe77` on 2026-11-20) is one repo with three parts:

- **Frontend** (repo root): React + Vite + TypeScript dashboard → GitHub Pages.
- **Backend** (`backend/`): FastAPI **read-only** observability API over SQLite, plus the
  scoring / optimizer / supervisor engine. **Not deployed** since the Fly.io app was cancelled in
  November 2026.
- **Engine**: an autonomous prompt-optimization loop that extracts structured metadata (authors,
  author affiliations, author-institution countries, sector, sub-sector) from impact-evaluation
  studies for 3ie's Development Evidence Portal, scores it against human-curated ground truth, and
  rewrites its own prompts within a quality gate.

This folder absorbed the old sibling `DEP/` workspace on **2026-08-21**; `DEP/` no longer exists.
Anything that still says otherwise is stale — report it rather than following it.

## Which document owns what

Keep each fact in exactly one place and link to it from the others:

| Doc | Owns |
|---|---|
| **This file** | Build/run commands, governance rules, stop rules, environment gotchas |
| [`backend/README.md`](backend/README.md) | Backend architecture, data model, **production deployment state** |
| [`ROADMAP.md`](ROADMAP.md) | Everything forward-looking; design decisions and their rationale |
| [`README.md`](README.md) | Public-facing project description |

`backend/README.md` § "Current deployment state & robustness" is the authority on what is deployed.
If this file and that section disagree, that section wins — check it first.

## Build / run / test

Python env is a local **`.venv/`** at the repo root (created 2026-08-21). Run backend modules as
packages **from the repo root**, never as file paths — they rely on package-relative imports:

```bash
.venv/Scripts/python -m backend.scripts.serve        # local API → http://127.0.0.1:8000
.venv/Scripts/python -m backend.scripts.<name>       # any other script
```

Set `$env:DEP_DB_PATH` to aim a script at a specific DB. The DB and corpus are **not** in the repo
(gitignored); build a local production subset with
`python -m backend.scripts.export_production_subset` → `backend/deploy/{promptlab.db,corpus/}`.

```bash
npm install && npm run dev     # → http://localhost:5173/promptlab/
npm run build                  # tsc -b && vite build
npm run lint                   # oxlint
npm test                       # vitest run

cd backend && pytest           # backend tests (pyproject sets pythonpath = [".."])
```

CI ([`.github/workflows/tests.yml`](.github/workflows/tests.yml)) runs `pytest -q` from `backend/`
on any push touching `backend/**`. There is **no** type-checker or Python linter in CI — `mypy` is
not a declared dependency of this project. If your editor runs it anyway, point
`MYPY_CACHE_DIR` outside this folder (see "Repo hygiene" below).

## Governance — the hard rule (do not weaken)

The agent moves **prompts** on its own. It must never move its own answer key or scoring rules —
that is the reward-hacking surface.

- **Prompts** → autonomous, within the gate.
- **Data** (ground truth, taxonomy) → human-approved. `scripts/audit_ground_truth.py` and
  `scripts/propose_gt_fixes.py` are **read-only** by design; keep them that way.
- **Code / eval-logic** → GitHub PR → human review → deploy.

## The quality gate — what it actually is

Read the gate through `scoring.gate_for()` / `scoring.gate_threshold_for(field)` and the miss-rate
floor through `scoring.safety_floor_ok()`. **Never read the bare `GATE_THRESHOLD` constant and never
re-implement the floor.** Field types come from `fields.py`.

| Field | `value_type` | Gated on | Floor |
|---|---|---|---|
| `authors`, `author_affiliation` | `list_text` | element-level **F1 ≥ 0.90** | recall ≥ 0.85 |
| `author_country`, `sub_sector` | `list_categorical` | element-level **F1 ≥ 0.90** | recall ≥ 0.85 |
| `sector_name` | `single_categorical` | **Cohen's κ ≥ 0.80** | macro sensitivity ≥ 0.70 * |

\* only when `sensitivity_gateable` — i.e. every class has ≥ `MIN_CLASS_SUPPORT` examples. Absent
data means "cannot judge", which must never fail a model.

Two traps that older versions of these instructions fell into:

- **`sector_name` is not gated on accuracy.** It is the sole entry in `scoring.FIELD_GATE`, gated on
  chance-corrected κ, because a fixed accuracy bar demands wildly different amounts of real skill
  depending only on how many classes a field happens to have.
- **`sub_sector` is not categorical.** The 3ie protocol makes it multi-valued, so it is a list field
  on F1 like the others (decided 2026-08-22 — see `ROADMAP.md`).

Scoring is concordance-aware: accent/mojibake folding, transliteration, fuzzy match at 95, and
`"A | B"` ground truth accepts either. **LLM-judged accuracy** (`app/judging.py`) is a reported
companion, never the gate.

> **Standing caveat.** Every threshold above is borrowed from the systematic-review literature, not
> measured on this corpus. The right reference is human inter-rater agreement, which nobody has
> measured here yet — that is what the blind double-extraction pack exists to produce. Do not defend
> any specific threshold as correct; say it is provisional, because it is.

## Stop rules / guardrails (don't remove without asking)

Production scale — `app/config.py`:
- `MAX_PRODUCTION_RECORDS = 200`, `PRODUCTION_ROLLOUT_STAGES = (100,)`. `run_extraction.py` clamps
  `--n` and warns if exceeded.

Optimizer — `app/optimizer.py`, deterministic at `seed=42`, self-terminating:
- `no_improve_limit=4`, `DEFAULT_BOLD_AFTER=2` (switch the reflector to structural rewrites),
  `DEFAULT_VAL_SIZE=50`, `DEFAULT_HOLDOUT_SIZE=30`, `DEFAULT_MINIBATCH_SIZE=8`.
- `DEFAULT_IMPROVEMENT_EPSILON=0.01`; `FIELD_IMPROVEMENT_EPSILON` raises `authors` and
  `author_affiliation` to **0.03** (high F1 variance on ~35 val records).
- A rewrite is accepted only if it beats the incumbent on the val set **and** holds on a
  cross-model holdout against `DEFAULT_HOLDOUT_REFERENCE` (`deepseek/deepseek-v4-flash`) — this is
  what blocks single-model overfits. val/holdout/train are disjoint and fixed per seed.

Per-(field, model) lifetime limits — `app/optimization_policy.py`:
- `LIFETIME_CAP = 25` candidates, then stop. `PLATEAU_WINDOW = 3` non-improving candidates after
  `MIN_ATTEMPTS = 5` ⇒ plateaued. Plateaued **and** > `TASK_LIMITED_GAP = 0.05` below the gate ⇒
  `task_limited`, which means escalate to a human, not try harder.

Model roster — `backend/models.yaml`: **4 models, 3 families** (trimmed from 12 on 2026-07-12
because cycling 12 through plateaued fields burned credits for no signal). The 4th
(`deepseek-v4-flash`) exists to be the cross-family holdout reference.

## Production: none

The Fly.io app (`dep-promptlab-api`) was cancelled in November 2026, so promptlab is **not deployed**.
The GitHub Pages frontend is **switched off** (20 November 2026): the repo moved to the
`Synthesis-and-Reviews-Office-3ie` organisation, and the `deploy.yml` workflow is disabled on GitHub,
because the dashboard would show no data without an API. Re-enable the workflow only together
with a live API.

**Status: frozen.** The portfolio registry (`Gen AI tools/_portfolio/`) records promptlab as frozen.
Its gate, scoring and stop-rule code is to become a shared library for the Assay lab and
EvidenceLoop. Add no new features here.

The container image (`Dockerfile`, `entrypoint.sh`) still builds and can be moved to another host.
It is a **read-only API**, and it starts the `worker` + `supervisor` only when `DEP_ENABLE_AGENTS=1`.
Neon Postgres is dead as well, and `api.py` tolerates a missing Postgres by design: don't "fix" that
try/except. How the Fly deployment worked is kept as history in `backend/README.md`.

## Environment gotchas (Windows)

- `git push` can show a red `NativeCommandError` in PowerShell even when it worked. Read the output, not
  the exit code.
- **`*.sh` must stay LF.** `.gitattributes` enforces it — a CRLF `entrypoint.sh` breaks the container.
- OpenRouter `~author/family-latest` aliases need the literal leading `~`.
- `run_extraction.py` commits each `(record, model)` result as it completes and skips already-done
  non-errored pairs, so an interrupted run resumes cleanly and errored records are retried.
- `corpus.read_md()` falls back to `config.MD_DIR`/`DEP_MD_DIR` + filename when `records.md_path`
  doesn't resolve on the current machine.
- Schema migrations: always test against a **copy** of a real DB. `db.init_db()` runs SCHEMA →
  `_migrate_to_multi_project` → additive `_migrate` → SCHEMA_INDEXES → `sync_projects`.
- PowerShell mangles quotes in inline `python -c "..."`. Write a temp `.py` and run that.

## Repo hygiene

This folder lives inside **OneDrive**, so anything on disk is synced. Keep it small:

- Regenerable caches (`.mypy_cache/`, `__pycache__/`, `node_modules/`, `.venv/`, `dist/`) are
  gitignored but *still sync*. If your editor runs mypy, set `MYPY_CACHE_DIR` to a path outside
  this folder — it otherwise grows a separate multi-hundred-MB cache per directory it runs in.
- Large local data (prod DB snapshots, the inspection DB, the stale-backend tarball) lives **outside
  OneDrive** at `C:\Users\LucasSempe\promptlab-local-data\`. Don't move it back in.
- `.gitignore` and `.dockerignore` both deliberately exclude the material merged from the old DEP
  workspace (`archive/`, `backups/`, `double-extraction/`, `*.xlsx`, `*.docx`, `*.pdf`, `*.zip`).
  `double-extraction/` and `backend/data/curator2_*` contain **full paper text and author names —
  PII**. Keep them out of git, out of the Docker context, and out of anything you publish.
- `archive/` is reference-only. `ops/` holds ad-hoc scripts from July 2026, most written to run inside
  the Fly container's `/data` volume. Fly is gone, so none of them is live. Treat them as unverified.

## Current work

- **Paper draft**: `paper/paper.qmd` (Quarto) — §4 results pending final optimization runs. Target
  JDE special issue, deadline 30 Sep 2026. `paper/references.bib` is CrossRef-verified.
- `feature/extraction-record-ids` is the only local branch with unmerged work.
