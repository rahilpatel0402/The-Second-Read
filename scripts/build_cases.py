"""
Build the two demonstration cases for The Second Read.

Both are fully synthetic (no PHI). Each case ships:
  - transcript:        the doctor-patient encounter (what the scribe heard)
  - note_under_review: the ambient-generated clinical note, pending signature
  - documents:         the interdisciplinary chart (PT / Nursing / OT) - the notes
                       the physician never saw, which the Second Read reconciles against

Case 1 (Eleanor Hayes)  -> a real drift: functional status contradicted by 3 disciplines.
Case 2 (Marcus Bell)    -> an apparent conflict that is actually consistent (distinct
                           Section GG tasks); the Second Read must stay silent.

Edit and re-run:  python scripts/build_cases.py
"""
import json
import os
import re

OUT_DIR = os.path.join(os.path.dirname(__file__), "..", "backend", "data", "cases")


def unwrap(t):
    """Join soft-wrapped lines within a paragraph; keep blank-line paragraph breaks."""
    paras = re.split(r"\n\s*\n", t.strip())
    return "\n\n".join(re.sub(r"\s*\n\s*", " ", p).strip() for p in paras)


def doc(id, type, discipline, author, timestamp, text, raw=False):
    body = text.strip() if raw else unwrap(text)
    return {"id": id, "type": type, "discipline": discipline, "author": author,
            "timestamp": timestamp, "provenance": "authored-for-demo",
            "text": body}


# ============================ CASE 1 — ELEANOR HAYES ============================
case1 = {
    "chart_id": "eleanor-hayes",
    "title": "Eleanor Hayes - POD 4, right hip hemiarthroplasty",
    "subtitle": "The catch",
    "expected": "clarification_recommended",
    "patient": {
        "name": "Eleanor Hayes", "mrn": "SNF-214402",
        "age": 79, "sex": "F", "setting": "SNF Rehab, Rm 214-B",
        "status": "POD 4, R hip hemi", "admit_date": "2026-07-14",
    },
    "transcript": doc(
        "TRANSCRIPT", "Doctor-Patient Encounter Transcript", "Provider",
        "Dr. A. Mensah, attending", "2026-07-18T11:40:00-07:00", """
DR: Morning, Eleanor. How are you feeling today?
PT: Oh, better, doctor. Much better than when I came in. I want to go home.
DR: I can hear that. The hip's healing nicely on the X-ray. How's the walking coming along?
PT: Good, I think. I've been using the walker. I get around.
DR: That's what I like to hear. Any pain when you walk?
PT: A little, but nothing like before. The therapy people have me up and moving.
DR: Good. And you feel steady on your feet with the walker?
PT: I manage. I've always been independent, you know. I did my own shopping right up until the fall.
DR: I remember. That's the goal, get you back to that. Let me listen to your heart and lungs... good.
    Incision looks clean, no redness. Let me just check the leg. Any numbness or tingling?
PT: No, no. It feels like my leg again.
DR: Excellent. Well, everything I'm seeing today looks like you're on track. Keep working with therapy,
    and if this pace holds we'll start talking about getting you home this week.
PT: Oh, that would be wonderful. My daughter's been asking.
DR: Let's aim for it. I'll check in again tomorrow.
""", raw=True),
    "note_under_review": doc(
        "NOTE", "Generated Clinical Note (DRAFT, pending signature)", "Provider",
        "Dr. A. Mensah, attending", "2026-07-18T11:52:00-07:00", """
Subjective: 79-year-old woman POD 4 from right hip hemiarthroplasty, admitted for rehabilitation
following a mechanical fall at home. Reports feeling substantially improved and is eager to return
home, where she lived independently prior to admission. Endorses mild incisional pain, well
controlled, without new numbness or paresthesia. Motivated and engaged with therapy.

Objective: Afebrile, vitals stable. Cardiovascular: regular rate and rhythm. Pulmonary: clear
bilaterally. Right hip incision clean, dry, intact, without erythema or drainage. Neurovascularly
intact distally. Post-operative radiograph reviewed, prosthesis in good alignment.

Functional status: Patient ambulating in hallway with rolling walker, steady gait, tolerating
therapy well.

Assessment & Plan: 1. Status post right hip hemiarthroplasty, POD 4, healing appropriately. Continue
current rehabilitation plan. 2. Functional recovery progressing. Anticipate discharge home in 5-7
days if current trajectory continues. 3. Continue DVT prophylaxis, pain management, and daily
therapy. 4. Will reassess tomorrow.
"""),
    "documents": [
        doc("PT-001", "Physical Therapy", "Physical Therapy", "PT",
            "2026-07-17T14:00:00-07:00", """
Gait training attempted. Patient required maximal assist of two for sit-to-stand. Ambulated 8 feet
with rolling walker and moderate assist before requesting to sit, reporting dizziness and fatigue.
Session terminated early.

Section GG revised: GG0170I walk 10 feet, 02 substantial/maximal assistance. GG0170D sit to stand,
02. Discharge readiness not yet established.
"""),
        doc("NUR-001", "Nursing", "Nursing", "RN",
            "2026-07-17T22:15:00-07:00", """
Patient found seated on floor at bedside at 22:05, attempting to self-transfer to bedside commode
without calling for assistance. No injury, neuro checks initiated per protocol. Second unwitnessed
transfer attempt this shift.

Bed alarm reactivated, hourly rounding initiated, provider notified via covering line. Fall risk
care plan updated.
"""),
        doc("OT-001", "Occupational Therapy", "Occupational Therapy", "OT",
            "2026-07-18T09:30:00-07:00", """
Toileting and self-care assessment. Patient requires contact guard to standby assist for toilet
transfers, unable to manage lower-body dressing independently secondary to hip precautions and
reduced standing tolerance.

Not safe for independent transfers at this time. Recommend continued OT, reassess in 3 days.
"""),
    ],
}

# ============================ CASE 2 — MARCUS BELL ============================
case2 = {
    "chart_id": "marcus-bell",
    "title": "Marcus Bell - POD 6, ischemic CVA (left hemiparesis)",
    "subtitle": "The silence",
    "expected": "supported",
    "patient": {
        "name": "Marcus Bell", "mrn": "SNF-118071",
        "age": 68, "sex": "M", "setting": "SNF Rehab, Rm 118-A",
        "status": "POD 6, CVA", "admit_date": "2026-07-12",
    },
    "transcript": doc(
        "TRANSCRIPT", "Doctor-Patient Encounter Transcript", "Provider",
        "Dr. S. Varghese, attending", "2026-07-18T10:20:00-07:00", """
DR: Good morning, Marcus. How's the arm and leg feeling today?
PT: The leg's coming back. The arm's still stubborn.
DR: That's often how it goes, the leg leads the way. I hear you did a good lap with the therapist this morning?
PT: Yeah. Walked down the hall and back with the walker. Girl just had to watch me, didn't have to hold me up.
DR: That's real progress. A week ago that wasn't happening. How about getting up out of the chair, standing?
PT: That's the hard part. Getting up, I need a good push. The left side doesn't want to help.
DR: Right, the weakness on the left makes that push-off tough. That'll keep improving as the strength comes back.
    Any trouble in the bed at night, turning over?
PT: The night folks help me shift around. Can't do that on my own yet.
DR: Understood. That's the left side again, it takes more to move in bed than it does to walk once you're up.
    Let me examine you... grip on the left is still weak, I can see that. Leg strength is better than last week.
    Sensation's intact. Good. You're moving in the right direction, Marcus.
PT: Slow though.
DR: Slow is fine. Slow and steady is exactly right after a stroke. Keep at it with the therapists.
""", raw=True),
    "note_under_review": doc(
        "NOTE", "Generated Clinical Note (DRAFT, pending signature)", "Provider",
        "Dr. S. Varghese, attending", "2026-07-18T10:34:00-07:00", """
Subjective: 68-year-old man POD 6 from ischemic CVA with residual left hemiparesis, admitted for
rehabilitation. Reports improving lower extremity function with persistent left upper extremity
weakness. Endorses difficulty with sit-to-stand secondary to left-sided weakness and requires
assistance with bed mobility. Engaged and motivated.

Objective: Afebrile, vitals stable. Cardiovascular: regular rate and rhythm. Neurologic: left grip
strength diminished, left lower extremity strength improved from prior exam, sensation intact
bilaterally, no new focal deficit.

Functional status: Ambulates 150 feet with rolling walker and supervision. Requires moderate assist
for transfers secondary to left-sided weakness. Progressing appropriately.

Assessment & Plan: 1. Ischemic CVA with left hemiparesis, POD 6, improving. Continue intensive
rehabilitation. 2. Left upper extremity weakness limiting transfers and bed mobility. Continue PT,
OT. 3. Continue secondary stroke prevention, antiplatelet and statin therapy. 4. Reassess in 2 days.
"""),
    "documents": [
        doc("PT-002", "Physical Therapy", "Physical Therapy", "PT",
            "2026-07-18T08:45:00-07:00", """
Ambulated 150 feet with rolling walker, supervision only, no physical assist required. Good
endurance, no loss of balance, one standing rest break. Gait speed improving. GG0170I walk 10 feet,
04 supervision. Continue gait training, advancing distance.
"""),
        doc("OT-002", "Occupational Therapy", "Occupational Therapy", "OT",
            "2026-07-18T09:15:00-07:00", """
Transfer and self-care assessment. Patient requires moderate assist for sit-to-stand and toilet
transfers secondary to left upper extremity weakness limiting push-off and grab-bar use. Standing
tolerance improving. GG0170D sit to stand, 03 moderate assistance. Continue OT, focus on transfer
mechanics.
"""),
        doc("NUR-002", "Nursing", "Nursing", "RN",
            "2026-07-18T06:40:00-07:00", """
Overnight care. Patient required two-person assist for repositioning and bed mobility per care plan
secondary to left hemiparesis. Assisted with turning q2h. No skin breakdown. Tolerated night without
complaint.
"""),
    ],
}


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    for case in (case1, case2):
        path = os.path.join(OUT_DIR, f"{case['chart_id']}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(case, f, indent=2, ensure_ascii=False)
        print(f"Wrote {path}  ({len(case['documents'])} interdisciplinary notes)")


if __name__ == "__main__":
    main()
