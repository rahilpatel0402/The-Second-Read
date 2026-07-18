"""Chart loading, search, and a FHIR / raw-record ingestion path."""
import glob
import json
import os
import re

DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CASES_DIR = os.path.join(DATA_DIR, "cases")


def list_charts():
    """Return [{id, title, patient_name}] for every hardcoded case."""
    out = []
    for path in sorted(glob.glob(os.path.join(CASES_DIR, "*.json"))):
        with open(path, encoding="utf-8") as f:
            c = json.load(f)
        out.append({
            "id": c["chart_id"],
            "title": c.get("title", c["chart_id"]),
            "patient_name": c["patient"]["name"],
        })
    return out


def load_chart(chart_id):
    path = os.path.join(CASES_DIR, f"{chart_id}.json")
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def default_chart():
    charts = list_charts()
    return load_chart(charts[0]["id"]) if charts else None


def get_document(chart, doc_id):
    for d in chart["documents"]:
        if d["id"] == doc_id:
            return d
    if chart["note_under_review"]["id"] == doc_id:
        return chart["note_under_review"]
    return None


def _tokens(text):
    return set(re.findall(r"[a-z0-9]+", text.lower()))


def search_chart(chart, query, limit=6):
    """Lightweight keyword-overlap search over the chart documents."""
    q = _tokens(query)
    scored = []
    for d in chart["documents"]:
        hay = f"{d['type']} {d['discipline']} {d['text']}"
        overlap = len(q & _tokens(hay))
        # small boost for query substrings appearing directly in the text
        substr = sum(1 for w in query.lower().split() if len(w) > 3 and w in hay.lower())
        score = overlap + substr
        if score > 0:
            snippet = d["text"].strip().replace("\n", " ")
            scored.append((score, {
                "id": d["id"],
                "type": d["type"],
                "discipline": d["discipline"],
                "timestamp": d["timestamp"],
                "snippet": snippet[:200] + ("..." if len(snippet) > 200 else ""),
            }))
    scored.sort(key=lambda x: -x[0])
    return [d for _, d in scored[:limit]]


# ---- Abridge FHIR ingestion (proves we speak their format) ----

def ingest_abridge_record(record):
    """Convert one raw Abridge synthetic-ambient-fhir record into a chart.

    Demonstrates that The Second Read ingests the provided FHIR/encounter format
    directly. The demo runs on a pre-built chart, but this path shows the loader.
    """
    pc = record["patient_context"]
    p = pc["patient"]
    name = p["name"][0]
    full_name = f"{''.join(name.get('prefix', ['']))} {' '.join(name['given'])} {name['family']}".strip()
    docs = [
        {
            "id": "TRANSCRIPT-ADMIT",
            "type": "Ambient Encounter Transcript",
            "discipline": "Provider",
            "author": "Ambient scribe",
            "timestamp": record["metadata"]["date"],
            "provenance": "abridge-synthetic",
            "text": record["transcript"],
        },
    ]
    ls = pc.get("longitudinal_summary", {})
    conds = ls.get("condition_labels", []) or []
    meds = ls.get("medication_labels", []) or []
    if conds or meds:
        docs.append({
            "id": "FHIR-PROBLEMS",
            "type": "Problem & Medication List (FHIR R4)",
            "discipline": "Structured EHR",
            "author": "EHR / Synthea FHIR",
            "timestamp": record["metadata"]["date"],
            "provenance": "abridge-synthetic",
            "text": "Conditions:\n" + "\n".join(f"  - {c}" for c in conds)
                    + "\n\nMedications:\n" + "\n".join(f"  - {m}" for m in meds),
        })
    return {
        "chart_id": record["metadata"].get("patient_id", "ingested"),
        "title": record["metadata"].get("visit_title", "Imported record"),
        "patient": {
            "name": full_name,
            "dob": p.get("birthDate", ""),
            "setting": record["metadata"].get("visit_title", ""),
            "admit_date": record["metadata"]["date"][:10],
        },
        "note_under_review": {
            "id": "NOTE-ADMIT",
            "type": "Provider Note (draft under review)",
            "discipline": "Provider",
            "author": "Attending",
            "timestamp": record["metadata"]["date"],
            "provenance": "imported",
            "text": record["note"],
        },
        "documents": docs,
    }


def normalize_import(obj):
    """Accept an uploaded/pasted record and return a chart in our format.

    Supports two shapes:
      1. Our native chart format (has note_under_review + documents).
      2. An Abridge synthetic-ambient-fhir record (has patient_context + note
         + transcript) -> converted via ingest_abridge_record.
    Raises ValueError if it recognizes neither.
    """
    if isinstance(obj, list) and obj:
        obj = obj[0]
    if not isinstance(obj, dict):
        raise ValueError("Import must be a JSON object.")
    if "note_under_review" in obj and "documents" in obj:
        obj.setdefault("chart_id", "imported")
        obj.setdefault("title", "Imported chart")
        obj.setdefault("patient", {"name": "Imported patient"})
        return obj
    if "patient_context" in obj and "note" in obj:
        return ingest_abridge_record(obj)
    raise ValueError(
        "Unrecognized format. Expected either a native chart "
        "(with note_under_review + documents) or an Abridge FHIR record "
        "(with patient_context + note + transcript)."
    )
