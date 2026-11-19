# PromptLab

Observability dashboard **and** autonomous prompt-optimization engine for **3ie's Development
Evidence Portal (DEP)** LLM data-extraction pipeline. It extracts structured metadata — authors,
author affiliations, author-institution countries, sector, sub-sector — from impact-evaluation
studies, scores every model against a human-curated ground truth, and **continuously improves the
prompts on its own, in the cloud**.

- **Frontend** (this repo root): React + Vite + TypeScript dashboard.
- **Backend** (`backend/`): FastAPI **read-only** API + scoring / optimizer / supervisor engine
  over a SQLite DB. See [`backend/README.md`](backend/README.md) for the full architecture and the
  detailed pipeline diagram.
- **Forward-looking plans**: [`ROADMAP.md`](ROADMAP.md).

## Architecture — two loops, different autonomy

The agent moves **prompts** on its own, but **data** (ground truth / taxonomy) and **code /
eval-logic** changes stay human-gated, so it can never edit its own answer key or scoring rules to
game the metric:

```mermaid
flowchart LR
    subgraph cloud["Cloud — autonomous (Fly.io supervisor)"]
      A["Loop A: optimize PROMPTS<br/>within the gate"]
      B["Loop B: audit ground truth,<br/>propose DATA fixes (planned)"]
    end
    A -->|"writes prompt_versions"| DB[("SQLite on /data")]
    B -->|"email diff + signed approval"| H{{"Human"}}
    H -->|"approves DATA edit"| DB
    CODE["Eval-logic / code change"] --> PR["GitHub PR"]
    PR --> HR{{"Human review"}}
    HR --> DEP["fly deploy"]
    DEP --> DB
    DB --> API["Read-only API"]
    API --> UI["Dashboard"]
```

The inner **extract → score → judge → gate → optimize → advance** loop (Loop A, run by the
`supervisor` daemon) is documented with its own diagram in
[`backend/README.md`](backend/README.md#architecture) and in the dashboard's "How to read this
dashboard" panel.

## What the dashboard shows

Metrics are tiered so the one that matters leads:

- **Quality gate (per model)** — the production metric. For **list fields** (authors, affiliations,
  countries, and sub-sector, which the 3ie protocol makes multi-valued): **element-level F1 ≥ 90%
  AND recall ≥ 85%**. The recall floor is separate because F1 alone allows a model to "pass" by
  over-predicting while still missing 20% of true values — missing values are invisible in QA while
  extras are visible and fixable. For the one **single-pick categorical field** (sector):
  **Cohen's κ ≥ 0.80**, with a macro-sensitivity floor of 0.70 where class support allows. κ rather
  than raw accuracy because accuracy isn't comparable across fields with different numbers of
  classes — a fixed 90% bar would demand very different amounts of real skill depending only on how
  many options a field happens to have, while κ is chance-corrected.
- **Explains the gate** — precision & recall (lists) or accuracy and per-class sensitivity
  (categorical), with 95% Wilson confidence intervals.
- **Corroboration** — cross-family **LLM-judge concordance**; confidence **calibration** (Brier).
- **Honesty** — abstain / wrong / hallucination mix and an honesty-adjusted score (which *steers
  the optimizer*), plus excerpt-verification (anti-fabrication).
- **Efficiency** — cost per model and an **EcoLogits-estimated CO₂e** footprint.
- **Comparisons** — sortable model table, a **quality leaderboard**, a **cost-vs-quality**
  frontier plot, confusion matrices, and prompt lineage + optimizer-progress charts.

## Development

```bash
npm install
npm run dev        # http://localhost:5173/promptlab/
```

The frontend reads from the API at `VITE_API_BASE_URL` (defaults to the local dev server
`http://127.0.0.1:8000`; the production build still points at the cancelled Fly.io app). Start the backend with
`python -m backend.scripts.serve` — see [`backend/README.md`](backend/README.md).

## Deploy

- **Frontend** → GitHub Pages, on push to `main`.
- **Backend** → not deployed. The Fly.io app was cancelled in November 2026. How it ran is kept as
  history in [`backend/README.md`](backend/README.md#production-deployment-flyio).
