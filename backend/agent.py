"""
The Second Read - agentic reconciliation, collapsed into one fast pass.

The note under review is reconciled against the rest of the chart (the
interdisciplinary PT / Nursing / OT notes the physician never saw, plus the
encounter transcript). A single model call:
  - builds a cited state ledger (verified facts),
  - reconciles the note per claim, applying CMS Section GG clinical judgment,
  - routes each real discrepancy and drafts the query,
  - and records apparent conflicts it examined and CLEARED (so no false alarms).

"No quote, no finding" is enforced in code: every quote is re-verified against
its source document; anything uncitable is dropped.
"""
import json
import os
import re

import anthropic
from dotenv import load_dotenv

from chart import get_document, all_documents

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MODEL = os.environ.get("THESECONDREAD_MODEL", "claude-sonnet-5")

_client = anthropic.Anthropic()


# ---------- citation verification (the integrity guarantee) ----------

def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def quote_in(quote, text):
    if not quote:
        return False
    return _norm(quote) in _norm(text)


# ---------- JSON ----------

def _text_of(message):
    return "".join(b.text for b in message.content if b.type == "text")


def _parse_json(raw):
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()
    start, end = raw.find("{"), raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end + 1]
    return json.loads(raw)


ANALYZE_SYSTEM = (
    "You are The Second Read. An ambient AI scribe wrote the note under review "
    "from the physician's visit alone. You read that note back against the rest of "
    "the chart - the interdisciplinary notes the physician never saw (physical "
    "therapy, nursing, occupational therapy) and the encounter transcript - and "
    "decide whether today's note still describes today's patient.\n\n"
    "CLINICAL JUDGMENT IS THE POINT - false alarms are as bad as misses. Function "
    "is measured per task under CMS Section GG: ambulation, sit-to-stand / transfers, "
    "and bed mobility are DISTINCT activities, each coded on a 6-level scale "
    "(06 independent, 05 setup, 04 supervision/contact-guard, 03 partial/moderate, "
    "02 substantial/maximal, 01 dependent or 2+ helpers). A single patient can "
    "genuinely be 04 to walk, 03 to transfer, and 01 for bed mobility - that is "
    "expected in hemiparesis and is NOT a contradiction.\n\n"
    "ACCURATE-BUT-COARSER IS NOT A FINDING. If the note's claim is true but simply "
    "less granular than the chart, the note is consistent - clear it. Example: the "
    "note says 'requires assistance with bed mobility' and nursing specifies "
    "'two-person assist' - two-person assist IS assistance, so the note is correct. "
    "Only raise a finding when the note asserts a status the chart CONTRADICTS for "
    "the SAME task (e.g. note implies steady/independent gait while therapy codes the "
    "walk task 02 substantial/maximal assist), or omits something that makes a stated "
    "claim or downstream plan unsafe.\n\n"
    "ONE FLAG PER SENTENCE: produce one finding per individual note sentence that is "
    "contradicted or made misleading by the chart. Each finding pairs exactly ONE "
    "draft sentence (note_quote, verbatim) with the specific chart evidence that "
    "contradicts THAT sentence, and a corrected version of THAT sentence. If two "
    "sentences are wrong (e.g. the functional-status line and the discharge-plan "
    "line), produce TWO findings. Never merge sentences into one finding, and never "
    "flag an accurate sentence (e.g. an accurate incision exam or post-op day).\n\n"
    "NO QUOTE, NO FINDING: note_quote is copied verbatim from the note; every "
    "evidence source_quote and ledger source_quote is copied verbatim from its "
    "document. Route functional/mobility/discharge drift to Physical Therapy "
    "(query_therapy); use query_nursing, query_provider, flag_stale, attributed_insert, "
    "or strike as appropriate.\n\n"
    "BE BRIEF AND ACTIONABLE:\n"
    "- Each evidence source_quote is the SHORTEST verbatim span that proves the "
    "mismatch (a clause, not the whole paragraph).\n"
    "- why_it_matters is ONE short sentence, at most ~18 words.\n"
    "- replacement: a corrected version of THIS sentence (note_quote), concise, "
    "clinically appropriate, attributed to the source discipline + date. It replaces "
    "the sentence in place when the clinician approves it, so it must read correctly "
    "as a drop-in for note_quote. For a contradiction, rewrite the sentence to match "
    "the chart; for an omission, rewrite it to incorporate the missing fact. Every "
    "finding MUST have a replacement.\n\n"
    "Return ONLY JSON:\n"
    "{\n"
    "  \"headline\": str, \"confidence\": int (0-100),\n"
    "  \"verified_consistent\": str (one line: the accurate parts you checked),\n"
    "  \"ledger\": [{\"fact\": str, \"value\": str, \"source_doc_id\": str, "
    "\"source_quote\": str, \"timestamp\": str, \"discipline\": str}],\n"
    "  \"findings\": [{\"note_quote\": str, \"replacement\": str, "
    "\"why_it_matters\": str, "
    "\"verdict\": \"contradicted\"|\"unsupported\"|\"stale\"|\"safety\", "
    "\"severity\": \"high\"|\"medium\"|\"low\", "
    "\"evidence\": [{\"source_doc_id\": str, \"source_quote\": str, "
    "\"discipline\": str, \"timestamp\": str}], "
    "\"action\": \"query_therapy\"|\"query_nursing\"|\"query_provider\"|"
    "\"flag_stale\"|\"attributed_insert\"|\"strike\", \"action_target\": str, "
    "\"drafted_text\": str}],\n"
    "  \"cleared\": [{\"apparent_conflict\": str, \"why_consistent\": str, "
    "\"items\": [{\"label\": str, \"source_doc_id\": str, \"source_quote\": str, "
    "\"discipline\": str, \"timestamp\": str}]}]\n"
    "}"
)


def analyze(chart, note_text):
    """One fast pass: returns the full validated result dict."""
    chart["note_under_review"]["text"] = note_text
    docs = all_documents(chart)
    docs_blob = "\n\n".join(
        f"[{d['id']}] {d['type']} ({d['discipline']}, {d['timestamp']}):\n{d['text']}"
        for d in docs
    )
    user = (
        f"NOTE UNDER REVIEW:\n\"\"\"\n{note_text}\n\"\"\"\n\n"
        f"THE REST OF THE CHART (quote verbatim from these):\n{docs_blob}"
    )
    resp = _client.messages.create(
        model=MODEL, max_tokens=6000,
        thinking={"type": "adaptive"},        # keeps the clinical judgment
        output_config={"effort": "medium"},   # ...but paces it for a live demo
        system=ANALYZE_SYSTEM,
        messages=[{"role": "user", "content": user}],
    )
    data = _parse_json(_text_of(resp))
    note = chart["note_under_review"]["text"]

    ledger = [e for e in data.get("ledger", [])
              if (d := get_document(chart, e.get("source_doc_id", "")))
              and quote_in(e.get("source_quote", ""), d["text"])]

    findings = []
    for f in data.get("findings", []):
        # a flag needs a verbatim draft sentence, >=1 cited evidence, and a replacement
        if not quote_in(f.get("note_quote", ""), note):
            continue
        if not (f.get("replacement") or "").strip():
            continue
        ev = [e for e in f.get("evidence", [])
              if (d := get_document(chart, e.get("source_doc_id", "")))
              and quote_in(e.get("source_quote", ""), d["text"])]
        if not ev:
            continue
        f["evidence"] = ev
        findings.append(f)

    cleared = []
    for c in data.get("cleared", []):
        c["items"] = [it for it in c.get("items", [])
                      if (d := get_document(chart, it.get("source_doc_id", "")))
                      and quote_in(it.get("source_quote", ""), d["text"])]
        cleared.append(c)

    return {
        "status": "clarification_recommended" if findings else "supported",
        "headline": data.get("headline", ""),
        "confidence": data.get("confidence"),
        "verified_consistent": data.get("verified_consistent", ""),
        "ledger": ledger,
        "findings": findings,
        "cleared": cleared,
        "docs_checked": len(docs),
        "note_text": note,
    }


# ---------- streamed wrapper (used by scripts/smoke.py) ----------

def run_review(chart, note_text, emit):
    for k, label in [("retrieve", "Reading the rest of the chart"),
                     ("extract", "Building the cited state ledger"),
                     ("reconcile", "Reconciling the note against the chart")]:
        emit({"type": "stage", "stage": k, "label": label})
    r = analyze(chart, note_text)
    emit({"type": "ledger", "entries": r["ledger"]})
    for f in r["findings"]:
        emit({"type": "finding", "finding": f})
    if r["cleared"]:
        emit({"type": "cleared", "cleared": r["cleared"]})
    emit({"type": "result", "status": r["status"], "headline": r["headline"],
          "confidence": r["confidence"], "verified_consistent": r["verified_consistent"],
          "findings_count": len(r["findings"]), "cleared_count": len(r["cleared"]),
          "docs_checked": r["docs_checked"]})
