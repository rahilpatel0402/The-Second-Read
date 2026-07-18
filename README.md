# The Second Read

**Every ambient AI scribe treats the doctor's words as truth and writes them down. The Second Read is the agent that reads the note back against the rest of the chart — and challenges the doctor's own input when the nursing, therapy, pharmacy, or dietitian record says the patient has changed.**

Built for the Abridge Hackathon. Target setting: **post-acute care / skilled nursing facilities (SNFs)**, where documentation *is* reimbursement (PDPM) and stale, contradictory charts cause both denied claims and patient harm.

## What it does

Given a clinician's note (an ambient-scribe output or a manual draft) and the rest of a patient's chart, The Second Read runs an agentic pipeline:

1. **Retrieve** — a real Claude tool-use loop; the agent chooses which chart documents to pull (`search_chart`, `read_document`).
2. **Extract** — builds a **cited state ledger**: each verified fact with a source quote, document id, and timestamp.
3. **Reconcile** — compares the note against the ledger, per claim, per PDPM and medication-safety standards.
4. **Route** — decides the action: strike, attributed insert, query a specific discipline, or flag the record as stale. *Routing is a decision, not a classification.*
5. **Act** — drafts the CDI query or attributed correction, addressed to the discipline whose record disagrees.

It is even-handed: it challenges the **provider** when therapy/nursing disagree, **and** flags another record as **stale** when the provider is the one who's right.

### "No quote, no finding" — enforced in code

Every finding and ledger entry must quote its source document **verbatim**. The backend re-verifies that each quote actually appears in the cited document (`agent.quote_in`); any finding it cannot cite is **suppressed, not guessed**. Hallucinated findings are structurally impossible to surface. This is the trust guarantee that makes a "challenge the doctor" tool safe to put in front of a clinician.

## The demo patient

**Monica Hilpert, 76, SNF admission for deconditioning** — a real record (#19) from Abridge's provided synthetic dataset. Running the default note surfaces three findings, each a different route:

- **Query → Therapy (PDPM impact):** the note describes ambulation the PT Section-GG eval contradicts — and GG drives the PDPM PT/OT case-mix, so the discrepancy moves reimbursement.
- **Attributed insert / safety:** the note starts **meperidine** on a 76-year-old — flagged against AGS Beers Criteria by the pharmacy consult.
- **Flag stale → Nursing:** the note's diet is correct and current; a nursing care plan carried from the hospital still says *NPO*. Here the **provider is right** and the nursing record is stale.

The note is **editable** — type a new claim and watch it get challenged (or cleared).

## Data provenance (what we built vs. what was provided)

- **Base documents** (provider admission note, ambient encounter transcript, FHIR problem/med list) are derived **verbatim from Abridge's provided synthetic dataset**, record #19. Tagged `abridge-synthetic`. All synthetic; no real patient data.
- **Ancillary SNF documents** (PT evaluation, pharmacy consult, dietitian consult, nursing care plan) are **authored by us** for the demo and tagged `authored-for-demo` in the UI. Abridge ships one encounter per patient; cross-discipline reconciliation needs the ancillary records a real SNF chart contains. The agent's *reasoning* is the product — these documents are the stage.
- `backend/chart.py` also includes `ingest_abridge_record()`, which converts a raw Abridge FHIR record into a chart — the loader speaks their format directly.

## Run it

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
```

Provide your Anthropic API key (from the hackathon's $100 credits) either as an
environment variable `ANTHROPIC_API_KEY`, or in a gitignored `backend/.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

Then:

```bash
cd backend
python -m uvicorn server:app --reload --port 8000
# open http://localhost:8000
```

Optional smoke test (no browser): `python scripts/smoke.py`

### Model configuration

Defaults to `claude-opus-4-8`. For a faster live demo you can override:

```
THESECONDREAD_MODEL=claude-sonnet-5
```

(`THESECONDREAD_RETRIEVE_MODEL` overrides just the retrieval loop.)

## Stack

Python · FastAPI (SSE streams the agent stage-by-stage to the browser) · Anthropic Claude (Opus 4.8, tool use) · vanilla HTML/JS frontend, served locally.

## Regenerating the demo chart

`backend/data/demo_chart.json` is committed and self-contained. To rebuild it from the Abridge dataset:

```bash
ABRIDGE_DATASET=/path/to/synthetic-ambient-fhir-25.jsonl python scripts/build_demo_chart.py
```
