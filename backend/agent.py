"""
The Second Read - agentic reconciliation pipeline.

Stages:
  RETRIEVE   - a real Claude tool-use loop: the model chooses which chart
               documents to pull (search_chart / read_document).
  EXTRACT    - build a cited "state ledger": each verified fact with a source
               quote, document id, and timestamp.
  RECONCILE  - compare the note against the ledger, per claim and per standard.
  ROUTE      - decide the action for each finding (strike / attributed insert /
               query a specific discipline / flag the record as stale).
  ACT        - draft the CDI query or attributed correction.

"No quote, no finding" is enforced IN CODE, not just in the prompt: every
finding and ledger entry must quote its source document verbatim, and we verify
the quote actually appears in the cited document. A claim we cannot cite is
suppressed, not guessed.
"""
import json
import os
import re

import anthropic
from dotenv import load_dotenv

from chart import get_document, search_chart, all_documents

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

MODEL = os.environ.get("THESECONDREAD_MODEL", "claude-opus-4-8")
RETRIEVE_MODEL = os.environ.get("THESECONDREAD_RETRIEVE_MODEL", MODEL)

_client = anthropic.Anthropic()


# ---------- citation verification (the integrity guarantee) ----------

def _norm(s):
    return re.sub(r"\s+", " ", (s or "").strip().lower())


def quote_in(quote, text):
    """True if `quote` appears in `text` verbatim (whitespace-insensitive)."""
    if not quote:
        return False
    return _norm(quote) in _norm(text)


# ---------- JSON parsing ----------

def _text_of(message):
    return "".join(b.text for b in message.content if b.type == "text")


def _parse_json(raw):
    raw = raw.strip()
    m = re.search(r"```(?:json)?\s*(.*?)```", raw, re.DOTALL)
    if m:
        raw = m.group(1).strip()
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1:
        raw = raw[start:end + 1]
    return json.loads(raw)


def _call_json(system, user, max_tokens=6000):
    resp = _client.messages.create(
        model=MODEL,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return _parse_json(_text_of(resp))


# ---------- STAGE 1: RETRIEVE (real tool-use loop) ----------

RETRIEVE_TOOLS = [
    {
        "name": "search_chart",
        "description": "Search the patient's chart for documents relevant to a "
                       "topic or claim. Returns matching documents with id, type, "
                       "discipline, timestamp, and a snippet.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look for, "
                          "e.g. 'functional status ambulation gait' or "
                          "'meperidine opioid safety' or 'diet NPO swallow'."}
            },
            "required": ["query"],
        },
    },
    {
        "name": "read_document",
        "description": "Read the full text of a chart document by its id.",
        "input_schema": {
            "type": "object",
            "properties": {"doc_id": {"type": "string"}},
            "required": ["doc_id"],
        },
    },
]

RETRIEVE_SYSTEM = (
    "You are the retrieval planner for The Second Read, an agent that audits a "
    "clinician's note against the rest of a skilled-nursing patient's chart. "
    "Your job in this stage is only to PULL the relevant documents. Read the "
    "note under review, then use search_chart and read_document to gather every "
    "document that could confirm or contradict any claim in the note - especially "
    "functional status / mobility, medications and their safety, and diet/nutrition. "
    "Read the full text of each relevant document. When you have gathered enough, "
    "reply with a one-sentence summary of what you pulled."
)


def stage_retrieve(chart, note_text, emit, max_turns=8):
    doc_index = "\n".join(
        f"  - {d['id']} | {d['type']} | {d['discipline']} | {d['timestamp']}"
        for d in all_documents(chart)
    )
    user = (
        f"NOTE UNDER REVIEW ({chart['note_under_review']['type']}):\n"
        f"\"\"\"\n{note_text}\n\"\"\"\n\n"
        f"Documents available in the chart:\n{doc_index}\n\n"
        "Pull every document relevant to verifying the note's claims."
    )
    messages = [{"role": "user", "content": user}]
    read_ids = []

    for _ in range(max_turns):
        resp = _client.messages.create(
            model=RETRIEVE_MODEL,
            max_tokens=1500,
            system=RETRIEVE_SYSTEM,
            tools=RETRIEVE_TOOLS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": resp.content})
        tool_uses = [b for b in resp.content if b.type == "tool_use"]
        if not tool_uses:
            break

        results = []
        for tu in tool_uses:
            if tu.name == "search_chart":
                q = tu.input.get("query", "")
                hits = search_chart(chart, q)
                emit({"type": "retrieve_action", "action": "search",
                      "query": q,
                      "found": [{"id": h["id"], "type": h["type"],
                                 "discipline": h["discipline"]} for h in hits]})
                results.append({"type": "tool_result", "tool_use_id": tu.id,
                                "content": json.dumps(hits)})
            elif tu.name == "read_document":
                did = tu.input.get("doc_id", "")
                d = get_document(chart, did)
                if d:
                    if did not in read_ids:
                        read_ids.append(did)
                    emit({"type": "retrieve_action", "action": "read",
                          "doc_id": did, "doc_type": d["type"],
                          "discipline": d["discipline"], "timestamp": d["timestamp"]})
                    results.append({"type": "tool_result", "tool_use_id": tu.id,
                                    "content": d["text"]})
                else:
                    results.append({"type": "tool_result", "tool_use_id": tu.id,
                                    "content": "Document not found.", "is_error": True})
        messages.append({"role": "user", "content": results})

    return read_ids


# ---------- STAGE 2: EXTRACT (cited state ledger) ----------

EXTRACT_SYSTEM = (
    "You are the extraction stage of The Second Read. From the chart documents, "
    "build a VERIFIED STATE LEDGER: the objective facts about this patient that "
    "the clinician's note should be checked against. Focus on facts that could "
    "confirm or contradict the note - functional/mobility status, medication "
    "orders and their safety standards, and diet/nutrition status. For EACH fact "
    "you MUST quote the source document verbatim. A fact you cannot quote must be "
    "omitted. Return ONLY JSON:\n"
    "{\"ledger\": [{\"fact\": str, \"value\": str, \"source_doc_id\": str, "
    "\"source_quote\": str (copied verbatim from that document), "
    "\"timestamp\": str, \"discipline\": str}]}"
)


def stage_extract(chart, doc_ids, emit):
    docs = [get_document(chart, i) for i in doc_ids]
    docs = [d for d in docs if d and d["id"] != chart["note_under_review"]["id"]]
    if not docs:
        docs = all_documents(chart)
    blob = "\n\n".join(
        f"[{d['id']}] {d['type']} ({d['discipline']}, {d['timestamp']}):\n{d['text']}"
        for d in docs
    )
    data = _call_json(EXTRACT_SYSTEM, f"CHART DOCUMENTS:\n{blob}")
    verified = []
    for e in data.get("ledger", []):
        d = get_document(chart, e.get("source_doc_id", ""))
        if d and quote_in(e.get("source_quote", ""), d["text"]):
            verified.append(e)
    emit({"type": "ledger", "entries": verified})
    return verified, docs


# ---------- STAGE 3-5: RECONCILE / ROUTE / ACT ----------

RECONCILE_SYSTEM = (
    "You are the reconciliation engine of The Second Read. An ambient AI scribe "
    "wrote the note under review from the physician's visit alone. You read that "
    "note back against the rest of the chart - the interdisciplinary notes the "
    "physician never saw (physical therapy, nursing, occupational therapy) and the "
    "encounter transcript - and decide whether today's note still describes today's "
    "patient.\n\n"
    "CLINICAL JUDGMENT IS THE POINT - false alarms are as bad as misses. Do not fire "
    "on surface-level number mismatches. Function is measured per task under CMS "
    "Section GG: ambulation, sit-to-stand / transfers, and bed mobility are DISTINCT "
    "tasks. A single patient can genuinely need supervision to walk, moderate assist "
    "to transfer, and two-person assist for bed mobility - that is expected in "
    "hemiparesis and is NOT a contradiction. Only raise a finding when the note's "
    "claim about a SPECIFIC task or fact is actually contradicted by the chart for "
    "that SAME task/fact.\n\n"
    "ACCURATE-BUT-COARSER IS NOT A FINDING. If the note's claim is true but simply "
    "less granular than the chart, the note is consistent - clear it, do not flag it. "
    "Example: the note says 'requires assistance with bed mobility' and nursing "
    "specifies 'two-person assist' - two-person assist IS assistance, so the note is "
    "correct and there is NO finding. Only flag when the note asserts a status the "
    "chart CONTRADICTS for the same task (e.g. the note says 'steady gait' or implies "
    "independence while therapy documents maximal assist), or when the note omits "
    "something that makes a stated claim or downstream plan unsafe.\n\n"
    "CONSOLIDATE. Produce ONE finding per underlying drift. When several note lines "
    "express or depend on the same drift - a functional-status claim and the "
    "discharge plan it drives - raise a SINGLE finding: put the primary drifting "
    "claim in note_quote, the driven decision line in downstream_quote, and attach "
    "ALL cross-discipline evidence to that one finding. Do not split one drift into "
    "multiple findings, and do not anchor a finding on an accurate or unrelated line "
    "(e.g. an accurate incision exam or post-op day).\n\n"
    "RULES (no quote, no finding):\n"
    "- note_quote MUST be copied verbatim from the note under review (the exact "
    "sentence/line carrying the drifting claim).\n"
    "- every evidence item's source_quote MUST be copied verbatim from its cited "
    "document. Cite EVERY discipline whose record bears on the claim.\n\n"
    "ROUTE each finding to the discipline that owns the contradicting measure. "
    "Functional / mobility / gait / discharge-readiness drift goes to the therapy "
    "discipline that owns the objective measure (Physical Therapy). Use query_nursing "
    "for nursing-owned records; query_provider when the provider must change their own "
    "note; flag_stale when a non-provider record is outdated and the provider is "
    "right; attributed_insert / strike for direct note edits. ACT by drafting the "
    "actual query text, addressed to action_target.\n\n"
    "Also identify CLEARED conflicts: apparent conflicts a shallow tool would fire "
    "on, which you examined and dismissed because they are actually consistent "
    "(e.g. different Section GG tasks at different assist levels). Explain why.\n\n"
    "Return ONLY JSON:\n"
    "{\n"
    "  \"headline\": str (one sentence a physician sees first),\n"
    "  \"confidence\": int (0-100),\n"
    "  \"verified_consistent\": str (one line naming what you checked and found "
    "accurate/consistent, so the physician trusts the rest of the note),\n"
    "  \"findings\": [{\"title\": str, \"note_quote\": str, "
    "\"downstream_quote\": str (optional: a note line whose decision this claim "
    "drives, e.g. a discharge or diet order, verbatim, else \"\"), "
    "\"verdict\": \"contradicted\"|\"unsupported\"|\"stale\"|\"safety\", "
    "\"severity\": \"high\"|\"medium\"|\"low\", \"why_it_matters\": str, "
    "\"evidence\": [{\"source_doc_id\": str, \"source_quote\": str, "
    "\"discipline\": str, \"timestamp\": str}], "
    "\"action\": \"query_therapy\"|\"query_nursing\"|\"query_provider\"|"
    "\"flag_stale\"|\"attributed_insert\"|\"strike\", "
    "\"action_target\": str, \"drafted_text\": str}],\n"
    "  \"cleared\": [{\"apparent_conflict\": str, \"why_consistent\": str, "
    "\"items\": [{\"label\": str, \"source_doc_id\": str, \"source_quote\": str, "
    "\"discipline\": str, \"timestamp\": str}]}]\n"
    "}"
)


def stage_reconcile(chart, note_text, ledger, docs, emit):
    ledger_blob = json.dumps(ledger, indent=2)
    docs_blob = "\n\n".join(
        f"[{d['id']}] {d['type']} ({d['discipline']}, {d['timestamp']}):\n{d['text']}"
        for d in docs
    )
    user = (
        f"NOTE UNDER REVIEW:\n\"\"\"\n{note_text}\n\"\"\"\n\n"
        f"VERIFIED STATE LEDGER:\n{ledger_blob}\n\n"
        f"THE REST OF THE CHART (for verbatim quoting):\n{docs_blob}"
    )
    data = _call_json(RECONCILE_SYSTEM, user, max_tokens=8000)
    note = chart["note_under_review"]["text"]

    findings = []
    for f in data.get("findings", []):
        if not quote_in(f.get("note_quote", ""), note):
            emit({"type": "suppressed", "title": f.get("title", "(untitled)")})
            continue
        ev = []
        for e in f.get("evidence", []):
            d = get_document(chart, e.get("source_doc_id", ""))
            if d and quote_in(e.get("source_quote", ""), d["text"]):
                ev.append(e)
        if not ev:
            emit({"type": "suppressed", "title": f.get("title", "(untitled)")})
            continue
        f["evidence"] = ev
        if f.get("downstream_quote") and not quote_in(f["downstream_quote"], note):
            f["downstream_quote"] = ""
        findings.append(f)
        emit({"type": "finding", "finding": f})

    cleared = []
    for c in data.get("cleared", []):
        items = []
        for it in c.get("items", []):
            d = get_document(chart, it.get("source_doc_id", ""))
            if d and quote_in(it.get("source_quote", ""), d["text"]):
                items.append(it)
        c["items"] = items
        cleared.append(c)
    if cleared:
        emit({"type": "cleared", "cleared": cleared})

    return {
        "findings": findings,
        "cleared": cleared,
        "headline": data.get("headline", ""),
        "confidence": data.get("confidence"),
        "verified_consistent": data.get("verified_consistent", ""),
    }


# ---------- orchestrator ----------

def run_review(chart, note_text, emit):
    # The note under review is whatever text was signed (may be edited/pasted),
    # so citation checks validate against exactly that.
    chart["note_under_review"]["text"] = note_text

    emit({"type": "stage", "stage": "retrieve", "label": "Reading the rest of the chart"})
    doc_ids = stage_retrieve(chart, note_text, emit)

    emit({"type": "stage", "stage": "extract", "label": "Building the cited state ledger"})
    ledger, docs = stage_extract(chart, doc_ids, emit)

    emit({"type": "stage", "stage": "reconcile", "label": "Reconciling the note against the chart, per claim"})
    r = stage_reconcile(chart, note_text, ledger, docs, emit)

    status = "clarification_recommended" if r["findings"] else "supported"
    emit({"type": "result",
          "status": status,
          "headline": r["headline"],
          "confidence": r["confidence"],
          "verified_consistent": r["verified_consistent"],
          "findings_count": len(r["findings"]),
          "cleared_count": len(r["cleared"]),
          "docs_checked": len(all_documents(chart)),
          "ledger_facts": len(ledger)})
