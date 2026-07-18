# The Second Read — Project Overview

**Every ambient AI scribe treats the doctor's words as truth and writes them down. The Second Read reads the note back against the rest of the chart — the notes the physician never saw (nursing at 10pm, therapy at 2pm) — and challenges it before the note is signed.**

Target setting: **post-acute care / skilled nursing facilities (SNFs)**, where documentation *is* reimbursement (PDPM) and stale or contradictory charts cause both denied claims and patient harm.

## Pipeline

The Second Read is **embedded in the "Sign note" action**. Signing runs a single citation-grounded reconciliation pass against the rest of the chart before the signature commits, reasoning in five steps:

1. **Retrieve** — the full interdisciplinary chart is pulled in for review: every PT, nursing, and OT note the physician never saw, plus the encounter transcript.
2. **Extract** — builds a **cited state ledger**: each verified fact with a source quote, document id, and timestamp.
3. **Reconcile** — compares the note against the ledger, per claim, applying clinical judgment (see [section-gg-reference.md](section-gg-reference.md)).
4. **Route** — decides the action: query the discipline that owns the contradicting measure, flag a stale record, attributed insert, or strike. *Routing is a decision, not a classification.*
5. **Act** — drafts the CDI query, addressed to the discipline whose record disagrees.

### "No quote, no finding" — enforced in code

Every finding and ledger entry must quote its source document **verbatim**. The backend (`agent.quote_in`) re-verifies that each quote actually appears in the cited document; any finding it cannot cite is **suppressed, not guessed**. This is the trust guarantee that makes a "challenge the doctor" tool safe in front of a clinician.

### Judgment, not false alarms

The Reconcile stage distinguishes a real discrepancy from an *apparent* conflict that is actually consistent. Consistent-but-apparent conflicts are surfaced as **cleared conflicts** with a reason, not fired as findings. This is what proves the tool has clinical judgment.

## The two demonstration cases

Both are fully synthetic (no PHI). Each ships the encounter **transcript**, the ambient-generated **clinical note** under review, and the **interdisciplinary chart** (PT / Nursing / OT) that the Second Read reconciles against.

- **Eleanor Hayes** — 79 F, POD 4 right hip hemiarthroplasty (*the catch*). The note records "steady gait" and anticipates discharge in 5–7 days, but PT (8 ft, maximal assist), nursing (unwitnessed fall), and OT (unsafe transfers) document the opposite. → **Clarification recommended**, functional line flagged, query routed to Physical Therapy; incision exam and post-op day verified consistent and *not* flagged.
- **Marcus Bell** — 68 M, POD 6 ischemic stroke (*the silence*). The note lists three different assist levels (supervision to walk, moderate assist to transfer, two-person assist for bed mobility) — three **distinct Section GG tasks** that legitimately differ in hemiparesis. → **Signs clean**, the apparent conflict considered and cleared.

## Run

```bash
python -m venv .venv && pip install -r requirements.txt   # once
# put your key in backend/.env  (ANTHROPIC_API_KEY=sk-ant-...)
cd backend && python -m uvicorn server:app --reload --port 8000
# open http://localhost:8000
```

Headless smoke test of a case: `python scripts/smoke.py <chart_id>` (e.g. `eleanor-hayes`, `marcus-bell`).

Model defaults to `claude-sonnet-5` (fast + keeps the judgment; single reconciliation pass at `medium` effort, ~13–18s). Override with `THESECONDREAD_MODEL=claude-opus-4-8` for maximum reasoning depth.

## Stack

Python · FastAPI · Anthropic Claude (Sonnet 5, adaptive thinking) · vanilla HTML/JS frontend served locally. Signing runs one reconciliation pass; the browser shows the five stages as an animated modal, then renders a two-column *"before you sign"* view (draft + highlighted drift / cited evidence) or a *"consistent"* confirmation. Cases live in `backend/data/cases/*.json`; the interdisciplinary notes live there as the evidence pool. `backend/chart.py` also ingests a native chart JSON or an Abridge FHIR record via the **Import** path.
