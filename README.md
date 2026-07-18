# The Second Read

**Every ambient AI scribe treats the doctor's words as truth and writes them down. The Second Read is the agent that reads the note back against the rest of the chart — and challenges the doctor's own input when the nursing, therapy, pharmacy, or dietitian record says the patient has changed.**

Built for the Abridge Hackathon. Target setting: **post-acute care / skilled nursing facilities (SNFs)**, where documentation *is* reimbursement (PDPM) and stale, contradictory charts cause both denied claims and patient harm.

## Why it matters

In a SNF, the **Section GG functional lines** the physician signs map directly to the **PDPM PT/OT case-mix groups that set the daily rate** — so a functional claim that contradicts therapy's own coding is at once a reimbursement error *and* an audit/denial trigger, because payers reconcile the signed note against the same interdisciplinary record this agent reads. And when the *chart* is the stale one — a MAR that hasn't caught up to a new anticoagulation order — the gap is **missed doses and stroke risk**. The Second Read catches both, at the one moment a human is already looking: **the signature**.

## What it does

The Second Read is **embedded in the "Sign note" action**. When the clinician signs an ambient-generated (or pasted) note, the agent reconciles it against the rest of the chart *before the signature commits* — a single citation-grounded pass that reasons in five steps:

1. **Retrieve** — the full interdisciplinary chart is pulled in for review: every PT, nursing, and OT note the physician never saw, plus the encounter transcript.
2. **Extract** — builds a **cited state ledger**: each verified fact with a source quote, document id, and timestamp.
3. **Reconcile** — compares the note against the ledger, per claim, applying clinical judgment (CMS Section GG tasks are distinct; accurate-but-coarser claims are not contradictions).
4. **Route** — decides the action: query the discipline that owns the contradicting measure, flag a stale record, attributed insert, or strike. *Routing is a decision, not a classification.*
5. **Act** — drafts the CDI query, addressed to the discipline whose record disagrees.

**If a discrepancy is found**, signing is interrupted with a *"Second read — before you sign"* card: the headline, a confidence score, the contradicting notes quoted with discipline + timestamp, why it matters, a drafted query, and Amend / Send query / Sign anyway / Dismiss.

**If the note holds up**, it signs — "checked against N interdisciplinary notes, consistent" — with an expandable *"considered and cleared K apparent conflicts"* so the clinician sees the judgment that was applied. No false alarms.

### "No quote, no finding" — enforced in code

Every finding and ledger entry must quote its source document **verbatim**. The backend re-verifies that each quote actually appears in the cited document (`agent.quote_in`); any finding it cannot cite is **suppressed, not guessed**. Hallucinated findings are structurally impossible to surface. This is the trust guarantee that makes a "challenge the doctor" tool safe to put in front of a clinician.

## The two demonstration cases

**Case 1 — Eleanor Hayes, 79 F, POD 4 right hip hemiarthroplasty ("the catch").** The note (built from a mid-day self-report visit) records "steady gait" and anticipates discharge in 5–7 days. But within the last 36 hours PT documents 8 feet at maximal assist, nursing documents an unwitnessed fall, and OT documents unsafe transfers. → **Clarification recommended**: the functional line is flagged, evidence cited from all three disciplines, a query routed to Physical Therapy — while the incision exam and post-op day are verified consistent and *not* flagged.

**Case 2 — Marcus Bell, 68 M, POD 6 ischemic stroke ("the silence").** The note lists three different assist levels — supervision to walk, moderate assist to transfer, two-person assist for bed mobility. A shallow tool fires a contradiction. The Second Read recognizes these as three **distinct Section GG tasks** that legitimately differ in hemiparesis. → **Signed clean**, 1–3 apparent conflicts considered and cleared. This is the case that proves clinical judgment and no false alarms.

The note is **editable** — paste or edit a claim and re-sign to watch it get challenged (or cleared).

## Data provenance

Every patient, note, and interdisciplinary record is **fully synthetic and authored for this demo** (no external dataset, no PHI). Each case ships the encounter **transcript**, the ambient-generated **clinical note** under review, and the **interdisciplinary chart** (PT / Nursing / OT) that lives in JSON and is what the Second Read reconciles against — the notes the physician never saw. `backend/chart.py` also includes `ingest_abridge_record()` / `normalize_import()`, so the **Import** path accepts a native chart JSON or an Abridge FHIR record directly.

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

**One-click launch / restart:** double-click **`scripts/start.bat`** (Windows). It frees port 8000 if something is stuck, starts the server with the venv, and opens the browser. A `Start The Second Read.bat` shortcut on the Desktop calls the same script.

Optional smoke test (no browser): `python scripts/smoke.py <chart_id>`

### Model configuration

Defaults to `claude-sonnet-5` (fast + keeps the clinical judgment; the review runs as a single reconciliation pass at `medium` effort, ~13–18s). For maximum reasoning depth you can override:

```
THESECONDREAD_MODEL=claude-opus-4-8
```

## Stack

Python · FastAPI · Anthropic Claude (Sonnet 5, adaptive thinking) · vanilla HTML/JS frontend, served locally. Signing runs one reconciliation pass; the browser shows the five stages as an animated modal while it runs, then renders the result — a two-column *"before you sign"* view (draft + highlighted drift on the left, cited evidence with timestamps on the right) or a clean *"consistent"* confirmation.

## Editing / adding cases

The cases live in `backend/data/cases/*.json` (self-contained, committed). Edit the clinical text in `scripts/build_cases.py` and re-run `python scripts/build_cases.py`, or drop a new JSON into `backend/data/cases/` — the UI picks it up automatically. Smoke-test a case headlessly with `python scripts/smoke.py <chart_id>`.
