"""
Build the hardcoded demo cases for The Second Read.

Both patients and every document are AUTHORED for the hackathon (no external
dataset). Each case is engineered so the agent surfaces distinct findings that
route to different actions - challenging the provider where therapy/nursing/
pharmacy disagree, and flagging another record as stale where the provider is
right.

Edit the text below (or add a third case) and re-run:
    python scripts/build_cases.py
"""
import json
import os

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "cases")


def doc(id, type, discipline, author, timestamp, text):
    return {"id": id, "type": type, "discipline": discipline, "author": author,
            "timestamp": timestamp, "provenance": "authored-for-demo",
            "text": text.strip()}


# ============================ CASE 1 ============================
case1 = {
    "chart_id": "eleanor-whitfield",
    "title": "Eleanor Whitfield - SNF rehab after CHF exacerbation & fall",
    "patient": {
        "name": "Eleanor Whitfield",
        "dob": "1944-06-18", "age": 81, "sex": "female",
        "mrn": "SNF-100281",
        "setting": "Skilled Nursing Facility - Cedar Ridge",
        "admit_date": "2026-02-10",
        "admit_reason": "Rehabilitation and deconditioning after CHF exacerbation and a mechanical fall",
    },
    "note_under_review": doc(
        "NOTE-ADMIT", "Provider Admission Note (draft under review)", "Provider",
        "Dr. Alvarez, MD (attending)", "2026-02-10T11:20:00-08:00",
        """
SKILLED NURSING FACILITY ADMISSION NOTE

Subjective: Mrs. Eleanor Whitfield is an 81-year-old woman admitted for
rehabilitation and continued skilled nursing care after a hospitalization for a
congestive heart failure exacerbation complicated by a mechanical fall at home.
She is eager to get back on her feet and return home. She denies chest pain,
shortness of breath at rest, dizziness, or new weakness. Sleep has been poor
since the hospital stay.

Objective: Alert and oriented, pleasant and cooperative, in no acute distress.
Lungs with mild bibasilar crackles, improved from admission. No lower-extremity
edema today. Patient ambulates approximately 100 feet with a rolling walker and
standby assist. Transfers with minimal assistance. Skin intact on my examination
today.

Assessment and Plan:

### Deconditioning and rehabilitation after CHF exacerbation
- Physical and occupational therapy to advance mobility and ADL independence
- Daily weights and fluid-status monitoring; continue home diuretic regimen

### Insomnia
- Continue diphenhydramine 50 mg at bedtime as needed for sleep

### Fall prevention
- Nonskid footwear and call-before-standing education reinforced
""",
    ),
    "documents": [
        doc("PT-EVAL-001", "Physical Therapy Initial Evaluation", "Physical Therapy",
            "R. Cho, PT, DPT", "2026-02-10T15:30:00-08:00", """
PHYSICAL THERAPY INITIAL EVALUATION
Date of service: 2026-02-10 15:30.

Functional status - Section GG admission performance (drives PDPM PT/OT case-mix):
  GG0170I Walk 10 feet: 02 - Substantial/maximal assistance
  GG0170D Sit-to-stand: 01 - Dependent
  Bed-to-chair transfer: 02 - Substantial/maximal assistance, two staff

Gait/mobility: Patient is non-ambulatory on evaluation and requires maximal
assistance of two for all transfers; she did not ambulate during this session.
Standing tolerance is limited to a few seconds with a two-person assist.

Assessment: The patient's mobility is markedly lower than the admission note
describes. She is not ambulating 100 feet with standby assist. Because the
Section GG scores set the PDPM PT/OT case-mix, the functional description in the
note should be reconciled before the MDS is finalized.
"""),
        doc("RX-CONSULT-001", "Pharmacy Consult - Geriatric Medication Review", "Pharmacy",
            "S. Patel, PharmD", "2026-02-10T16:45:00-08:00", """
PHARMACY CONSULT - GERIATRIC MEDICATION REVIEW
Reviewed admission medication orders for Mrs. Whitfield (age 81).

SAFETY FLAG: Diphenhydramine is a strongly anticholinergic agent listed on the
2023 AGS Beers Criteria as potentially inappropriate in adults 65 and older,
associated with confusion, falls, and delirium. This risk is heightened in a
patient admitted after a fall.

Recommendation: Avoid diphenhydramine for sleep. Consider nonpharmacologic sleep
measures and, if needed, a lower-risk agent such as low-dose melatonin. Recommend
the attending discontinue the diphenhydramine order.
"""),
        doc("NURSING-SKIN-001", "Nursing Admission Skin Assessment", "Nursing",
            "M. Torres, RN", "2026-02-10T13:05:00-08:00", """
NURSING ADMISSION SKIN ASSESSMENT
Completed: 2026-02-10 13:05 by the admitting RN.

Braden score: 14 (moderate risk).
Skin findings: Admission skin assessment: Stage 2 pressure injury noted to the
right heel, 1.5 cm, with a shallow open area. Photograph on file. An offloading
heel boot was applied and a wound-care consult was placed.

This differs from the provider admission note, which documents intact skin.
"""),
    ],
}

# ============================ CASE 2 ============================
case2 = {
    "chart_id": "marcus-bell",
    "title": "Marcus Bell - SNF rehab after ischemic stroke",
    "patient": {
        "name": "Marcus Bell",
        "dob": "1957-09-02", "age": 68, "sex": "male",
        "mrn": "SNF-100437",
        "setting": "Skilled Nursing Facility - Cedar Ridge",
        "admit_date": "2026-03-05",
        "admit_reason": "Rehabilitation after left MCA ischemic stroke",
    },
    "note_under_review": doc(
        "NOTE-ADMIT", "Provider Admission Note (draft under review)", "Provider",
        "Dr. Alvarez, MD (attending)", "2026-03-05T11:00:00-08:00",
        """
SKILLED NURSING FACILITY ADMISSION NOTE

Subjective: Mr. Marcus Bell is a 68-year-old man admitted for rehabilitation
after a left middle cerebral artery ischemic stroke. He has residual right-sided
weakness and reports his speech and swallowing "feel almost back to normal." He
is motivated and independent-minded.

Objective: Alert, oriented, mild expressive aphasia, mild right facial droop.
Right upper and lower extremity strength 4-/5. He fed himself lunch without
obvious difficulty during my visit. Diet: regular, no restrictions. Patient is
modified independent with activities of daily living.

Assessment and Plan:

### Ischemic stroke, cardioembolic (atrial fibrillation)
- Started apixaban 5 mg twice daily for cardioembolic stroke prevention
- Continue rehabilitation with physical, occupational, and speech therapy

### Rehabilitation
- Advance mobility and self-care as tolerated
""",
    ),
    "documents": [
        doc("SLP-EVAL-001", "Speech-Language Pathology - Bedside Swallow Evaluation", "Physical Therapy",
            "K. Adeyemi, MS, CCC-SLP", "2026-03-05T16:00:00-08:00", """
SPEECH-LANGUAGE PATHOLOGY - BEDSIDE SWALLOW EVALUATION
Date of service: 2026-03-05 16:00.

Speech-language pathology bedside swallow evaluation reveals moderate
oropharyngeal dysphagia with delayed swallow initiation and overt signs of
aspiration on thin liquids (wet vocal quality, coughing after swallows).
Recommend nectar-thick liquids and a mechanical soft diet with aspiration
precautions and supervision at meals.

A regular, unrestricted diet is not safe for this patient at this time.
"""),
        doc("MAR-001", "Medication Administration Record (carried from prior records)", "Nursing",
            "Prior-records transfer packet", "2026-03-03T09:00:00-08:00", """
MEDICATION ADMINISTRATION RECORD (carried from prior records)
Last reconciled: 2026-03-03 (acute hospital, before the SNF transfer).

Active medications:
  - aspirin 81 mg once daily
  - atorvastatin 40 mg once daily
  - lisinopril 10 mg once daily

No oral anticoagulant listed. This MAR has not been reconciled with the SNF
admission orders.
"""),
        doc("OT-EVAL-001", "Occupational Therapy Initial Evaluation", "Occupational Therapy",
            "D. Fischer, OTR/L", "2026-03-05T15:20:00-08:00", """
OCCUPATIONAL THERAPY INITIAL EVALUATION
Date of service: 2026-03-05 15:20.

Self-care - Section GG admission performance:
  GG0130A Eating: 04 - Supervision/touching assistance
  GG0130B Oral hygiene: 03 - Partial/moderate assistance
  GG0130C Toileting hygiene: 03 - Partial/moderate assistance
  Upper-body dressing: 03 - Partial/moderate assistance
  Lower-body dressing and bathing: 03 - Partial/moderate assistance

Occupational therapy evaluation: patient requires moderate assistance for upper-
and lower-body dressing and bathing; he is not independent with ADLs. The Section
GG self-care scores support a substantially higher assistance level than the
admission note's "modified independent" description, and drive the PDPM case-mix.
"""),
    ],
}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for case in (case1, case2):
        path = os.path.join(OUT_DIR, f"{case['chart_id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(case, f, indent=2, ensure_ascii=False)
        print(f"Wrote {path}  ({len(case['documents'])} docs)")


if __name__ == "__main__":
    main()
