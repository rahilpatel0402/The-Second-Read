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

from chart import get_document, search_chart

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
        for d in chart["documents"]
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
    docs = [get_document(chart, i) for i in doc_ids] or chart["documents"]
    docs = [d for d in docs if d]
    if not docs:
        docs = chart["documents"]
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
    "You are the reconciliation engine of The Second Read. Every ambient AI "
    "scribe treats the clinician's words as truth. You do not. You read the note "
    "back against the verified state ledger and the rest of the chart, and you "
    "challenge the note - including the provider's own input - wherever the "
    "nursing, therapy, pharmacy, or dietitian record disagrees. You are also "
    "even-handed: when the provider is RIGHT and it is another record that is out "
    "of date, you flag THAT record as stale rather than the provider.\n\n"
    "For each discrepancy produce a finding. RULES:\n"
    "- note_quote MUST be copied verbatim from the note under review.\n"
    "- source_quote MUST be copied verbatim from the cited chart document.\n"
    "- If you cannot quote both sides, do not raise the finding (no quote, no finding).\n"
    "- Consider PDPM standards (e.g. Section GG function drives PT/OT case-mix) "
    "and medication-safety standards (e.g. AGS Beers Criteria).\n\n"
    "Then ROUTE each finding - this is a DECISION about who must act next, not a "
    "label. Address the action to the discipline that OWNS the contradicting fact:\n"
    "  query_therapy: function / mobility / ADL / swallow discrepancies - Therapy "
    "(PT, OT, or SLP) owns the objective measure. Route to them to reconcile the "
    "level and align the MDS Section GG (state the PDPM impact).\n"
    "  query_nursing: a nursing-owned record (skin assessment, care plan, MAR, "
    "flowsheet) must be confirmed or updated.\n"
    "  query_provider: the provider must amend their own note or make a clinical "
    "decision (e.g., changing a medication order).\n"
    "  attributed_insert: draft an attributed clarification to insert into the note "
    "for provider approval - use for clear, low-ambiguity corrections.\n"
    "  flag_stale: a NON-provider record is out of date while the provider/current "
    "data are right - flag that record and route its update to the owning discipline.\n"
    "  strike: remove an unsupportable statement from the note.\n"
    "Prefer routing to the discipline that owns the contradicting fact; reserve "
    "query_provider for when the provider's own documentation or a clinical decision "
    "is what must change.\n\n"
    "For each finding also set:\n"
    "  verdict: one of contradicted | unsupported | stale | safety\n"
    "  action_target: the specific discipline/role the drafted text is addressed to\n"
    "  drafted_text: the actual CDI query or attributed correction to send, "
    "written professionally and addressed to action_target.\n\n"
    "Return ONLY JSON:\n"
    "{\"findings\": [{\"title\": str, \"note_quote\": str, \"source_doc_id\": str, "
    "\"source_quote\": str, \"timestamp\": str, \"discipline\": str, "
    "\"verdict\": str, \"severity\": \"high\"|\"medium\"|\"low\", "
    "\"category\": str, \"pdpm_impact\": str, \"rationale\": str, "
    "\"action\": str, \"action_target\": str, \"drafted_text\": str}]}"
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
        f"FULL CHART DOCUMENTS (for verbatim quoting):\n{docs_blob}"
    )
    data = _call_json(RECONCILE_SYSTEM, user, max_tokens=8000)
    note = chart["note_under_review"]["text"]
    findings = []
    for f in data.get("findings", []):
        d = get_document(chart, f.get("source_doc_id", ""))
        note_ok = quote_in(f.get("note_quote", ""), note)
        src_ok = d is not None and quote_in(f.get("source_quote", ""), d["text"])
        if note_ok and src_ok:
            f["verified"] = True
            findings.append(f)
            emit({"type": "finding", "finding": f})
        else:
            emit({"type": "suppressed", "reason": "uncitable",
                  "title": f.get("title", "(untitled)"),
                  "note_quote_ok": note_ok, "source_quote_ok": src_ok})
    return findings


# ---------- orchestrator ----------

def run_review(chart, note_text, emit):
    emit({"type": "stage", "stage": "retrieve", "label": "Retrieving relevant chart documents"})
    doc_ids = stage_retrieve(chart, note_text, emit)

    emit({"type": "stage", "stage": "extract", "label": "Building the cited state ledger"})
    ledger, docs = stage_extract(chart, doc_ids, emit)

    emit({"type": "stage", "stage": "reconcile", "label": "Reconciling the note against the chart, per claim"})
    findings = stage_reconcile(chart, note_text, ledger, docs, emit)

    emit({"type": "done",
          "summary": {
              "documents_retrieved": len(doc_ids),
              "ledger_facts": len(ledger),
              "findings": len(findings),
          }})
