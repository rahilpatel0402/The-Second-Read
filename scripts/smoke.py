"""End-to-end smoke test of the pipeline (no server). Prints every event.

    python scripts/smoke.py [chart_id]
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

from chart import load_chart, default_chart  # noqa: E402
from agent import run_review  # noqa: E402


def main():
    chart_id = sys.argv[1] if len(sys.argv) > 1 else None
    chart = load_chart(chart_id) if chart_id else default_chart()
    print(f"Case: {chart['patient']['name']} ({chart['chart_id']})")
    note = chart["note_under_review"]["text"]

    def emit(ev):
        t = ev.get("type")
        if t == "stage":
            print(f"\n=== STAGE: {ev['stage'].upper()} — {ev['label']} ===")
        elif t == "ledger":
            print(f"  ledger: {len(ev['entries'])} verified facts")
            for e in ev["entries"]:
                print(f"    - {e['fact']}: {e['value']}  [{e['source_doc_id']}]")
        elif t == "finding":
            f = ev["finding"]
            print(f"\n  FINDING [{f.get('action')} -> {f.get('action_target')}] {f.get('title','')}")
            print(f"    verdict={f.get('verdict')} severity={f.get('severity')}")
            print(f"    note:   {f.get('note_quote','')[:90]!r}")
            for e in f.get("evidence", []):
                print(f"    src [{e['discipline']}/{e['source_doc_id']}]: {e['source_quote'][:80]!r}")
            print(f"    fix:   {f.get('replacement','')[:110]}")
            print(f"    query: {f.get('drafted_text','')[:110]}")
        elif t == "cleared":
            print(f"\n  CLEARED {len(ev['cleared'])} apparent conflict(s):")
            for c in ev["cleared"]:
                print(f"    - {c['apparent_conflict']}: {c['why_consistent'][:100]}")
        elif t == "suppressed":
            print(f"  SUPPRESSED (uncitable): {ev['title']}")
        elif t == "result":
            print(f"\n=== RESULT: {ev['status'].upper()}  (confidence {ev.get('confidence')}) ===")
            print(f"    headline: {ev.get('headline')}")
            print(f"    verified_consistent: {ev.get('verified_consistent')}")
            print(f"    findings={ev['findings_count']} cleared={ev['cleared_count']} docs_checked={ev['docs_checked']}")
        elif t == "error":
            print(f"\n!!! ERROR: {ev['message']}")

    run_review(chart, note, emit)


if __name__ == "__main__":
    main()
