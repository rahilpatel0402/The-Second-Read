"""
Build the demo chart for The Second Read.

The BASE patient documents (provider admission note, ambient encounter
transcript, FHIR problem/medication list) are derived verbatim from Abridge's
provided synthetic dataset (`synthetic-ambient-fhir-25`, record #19 - Monica
Hilpert, a skilled-nursing-facility admission). Everything is synthetic; no real
patient data is present.

The ANCILLARY SNF documents (PT evaluation, pharmacy consult, dietitian consult,
nursing care plan) are AUTHORED BY US for the hackathon. Abridge ships one
encounter per patient, but the whole point of The Second Read is cross-discipline
reconciliation, so we add the realistic ancillary records a real SNF chart would
contain. Each is tagged provenance="authored-for-demo".

Run once to regenerate backend/data/demo_chart.json:
    python scripts/build_demo_chart.py
"""
import json
import os

DATASET = os.environ.get(
    "ABRIDGE_DATASET",
    "C:/Users/rahil/Downloads/synthetic-ambient-fhir-25/synthetic-ambient-fhir-25/synthetic-ambient-fhir-25.jsonl",
)
OUT = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "demo_chart.json")


def load_record(idx=19):
    with open(DATASET, encoding="utf-8") as f:
        recs = [json.loads(line) for line in f]
    return recs[idx]


def build():
    r = load_record(19)
    pc = r["patient_context"]
    patient = pc["patient"]
    ls = pc.get("longitudinal_summary", {})

    # ---- Patient header (from real Abridge synthetic record) ----
    name = patient["name"][0]
    full_name = f"{name['prefix'][0]} {' '.join(name['given'])} {name['family']}"
    patient_hdr = {
        "name": full_name,
        "dob": patient["birthDate"],
        "age": 76,
        "sex": patient.get("gender", ""),
        "mrn": "SNF-0000014",
        "setting": "Skilled Nursing Facility - Maple Grove",
        "admit_date": r["metadata"]["date"][:10],
        "admit_reason": "Deconditioning and rehabilitation after acute hospitalization",
    }

    # ---- Note under review (REAL Abridge provider admission note) ----
    note_under_review = {
        "id": "NOTE-ADMIT",
        "type": "Provider Admission Note (draft under review)",
        "discipline": "Provider",
        "author": "Dr. Reyes, MD (attending)",
        "timestamp": r["metadata"]["date"],
        "provenance": "abridge-synthetic",
        "text": r["note"],
    }

    # ---- FHIR-derived problem & medication list (real longitudinal data) ----
    conds = ls.get("condition_labels", []) or []
    meds = ls.get("medication_labels", []) or []
    problem_list = "ACTIVE PROBLEM LIST (FHIR longitudinal record)\n"
    problem_list += "Conditions:\n" + "\n".join(f"  - {c}" for c in conds[:20]) + "\n\n"
    problem_list += "Medications on file:\n" + "\n".join(f"  - {m}" for m in meds[:20])

    docs = []

    # Real ambient encounter transcript
    docs.append({
        "id": "TRANSCRIPT-ADMIT",
        "type": "Ambient Encounter Transcript",
        "discipline": "Provider",
        "author": "Ambient scribe (DR / NURSE / PT)",
        "timestamp": r["metadata"]["date"],
        "provenance": "abridge-synthetic",
        "text": r["transcript"],
    })

    # Real FHIR problem/med list
    docs.append({
        "id": "FHIR-PROBLEMS",
        "type": "Problem & Medication List (FHIR R4)",
        "discipline": "Structured EHR",
        "author": "EHR / Synthea FHIR",
        "timestamp": r["metadata"]["date"],
        "provenance": "abridge-synthetic",
        "text": problem_list,
    })

    # ---- AUTHORED ancillary SNF documents (clearly disclosed) ----

    # 1) PT eval - contradicts the note's functional-status claim (PDPM-relevant)
    docs.append({
        "id": "PT-EVAL-001",
        "type": "Physical Therapy Initial Evaluation",
        "discipline": "Physical Therapy",
        "author": "J. Okafor, PT, DPT",
        "timestamp": "2023-11-27T15:10:00-08:00",
        "provenance": "authored-for-demo",
        "text": (
            "PHYSICAL THERAPY INITIAL EVALUATION\n"
            "Date of service: 2023-11-27 15:10 (same admission day, standardized assessment).\n\n"
            "Functional status - Section GG admission performance (used for PDPM PT/OT case-mix):\n"
            "  GG0170I Walk 10 feet: 02 - Substantial/maximal assistance\n"
            "  GG0170J Walk 50 feet with two turns: 88 - Not attempted due to safety concerns\n"
            "  GG0170D Sit-to-stand: 01 - Dependent\n"
            "  Bed-to-chair transfer: 02 - Substantial/maximal assistance, two staff required\n\n"
            "Gait: Patient is non-ambulatory on evaluation; unable to stand or step without "
            "two-person maximal assistance. She did not ambulate any distance during this session.\n\n"
            "Assessment: Patient presents at a substantially lower functional level than the "
            "admission note reflects. She is NOT currently ambulating supervised distances; she "
            "requires maximal two-person assistance for all mobility. The admission-note functional "
            "description should be reconciled, as the Section GG scores drive the PDPM PT/OT "
            "case-mix and reimbursement."
        ),
    })

    # 2) Pharmacy consult - Beers-criteria safety flag on meperidine
    docs.append({
        "id": "RX-CONSULT-001",
        "type": "Pharmacy Consult - Geriatric Medication Review",
        "discipline": "Pharmacy",
        "author": "S. Patel, PharmD",
        "timestamp": "2023-11-27T16:40:00-08:00",
        "provenance": "authored-for-demo",
        "text": (
            "PHARMACY CONSULT - GERIATRIC MEDICATION REVIEW\n"
            "Reviewed admission medication orders for Mrs. Hilpert (age 76).\n\n"
            "SAFETY FLAG: Meperidine (Demerol) is identified on the 2023 AGS Beers Criteria as a "
            "potentially inappropriate medication in adults 65 and older. Its active metabolite "
            "normeperidine accumulates and is neurotoxic, raising the risk of delirium, confusion, "
            "and seizures, especially with the reduced renal clearance common in older adults.\n\n"
            "Recommendation: Avoid meperidine for this patient. Consider scheduled acetaminophen "
            "with a low-dose non-meperidine opioid and a bowel regimen if breakthrough analgesia is "
            "needed. Recommend the attending discontinue the meperidine order."
        ),
    })

    # 3) Dietitian consult - CURRENT, supports the provider (diet is texture-modified, not NPO)
    docs.append({
        "id": "RD-CONSULT-001",
        "type": "Registered Dietitian Consult",
        "discipline": "Dietitian",
        "author": "L. Nguyen, RD",
        "timestamp": "2023-11-27T14:20:00-08:00",
        "provenance": "authored-for-demo",
        "text": (
            "REGISTERED DIETITIAN CONSULT\n"
            "Date of service: 2023-11-27 14:20.\n\n"
            "Assessment completed today at the SNF. Patient is tolerating oral intake. No active "
            "dysphagia signs on meal observation; she manages soft, texture-modified foods, chewing "
            "on one side due to extensive tooth loss.\n\n"
            "Plan: Texture-modified (mechanical soft) oral diet, protein- and calcium-forward, "
            "balanced for glucose and lipids. Patient is NOT NPO. Recommend discontinuing any "
            "carried-forward NPO or swallow-precaution orders from the transferring hospital, which "
            "no longer reflect the patient's status."
        ),
    })

    # 4) Nursing care plan - STALE (carried from hospital transfer, not reconciled)
    docs.append({
        "id": "NURSING-CAREPLAN-001",
        "type": "Nursing Care Plan (carried from acute hospital transfer)",
        "discipline": "Nursing",
        "author": "Acute hospital transfer packet",
        "timestamp": "2023-11-25T09:00:00-08:00",
        "provenance": "authored-for-demo",
        "text": (
            "NURSING CARE PLAN (carried from acute hospital transfer)\n"
            "Entered: 2023-11-25 09:00 (acute hospital, during discharge planning - two days "
            "before SNF admission).\n\n"
            "Nutrition: Diet: NPO - pending bedside swallow evaluation. Aspiration precautions in "
            "place.\n"
            "Mobility: Bed rest with assistance.\n\n"
            "NOTE: This care plan was transferred from the acute hospital and has NOT been "
            "reconciled with the SNF admission orders or the SNF dietitian assessment."
        ),
    })

    chart = {
        "chart_id": "monica-hilpert-snf",
        "patient": patient_hdr,
        "source_note": (
            "Base documents (admission note, transcript, FHIR problem list) are derived from "
            "Abridge's provided synthetic dataset, record #19. Ancillary SNF documents "
            "(PT, pharmacy, dietitian, nursing care plan) are authored by us for the demo and "
            "tagged provenance='authored-for-demo'. All content is synthetic."
        ),
        "note_under_review": note_under_review,
        "documents": docs,
    }

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(chart, f, indent=2, ensure_ascii=False)
    print(f"Wrote {OUT}")
    print(f"  note under review: {len(note_under_review['text'])} chars")
    print(f"  {len(docs)} chart documents")


if __name__ == "__main__":
    build()
