# CMS Section GG — Functional Coding Reference

The Second Read's functional reconciliation reasons over **CMS Section GG**
(Functional Abilities and Goals). Section GG0130 covers self-care and GG0170
covers mobility; each *activity* is coded separately using a 6-level scale based
on how much a helper assists.

Source: CMS, *Coding Section GG Self-Care & Mobility Activities Included on the
Post-Acute Care Item Sets* (decision tree). Summarized here as design reference.

## The 6-point scale (higher = more independent)

| Code | Level | Meaning |
|------|-------|---------|
| **06** | Independent | Completes the activity safely, no helper. |
| **05** | Setup / clean-up assistance | Helper only sets up or cleans up before/after; patient does the activity. |
| **04** | Supervision / touching assistance | Verbal cues and/or steadying / touching / **contact guard**. |
| **03** | Partial / moderate assistance | Helper does **less than half** the effort. |
| **02** | Substantial / maximal assistance | Helper does **more than half** the effort. |
| **01** | Dependent | Helper does **all** the effort, **or 2+ helpers are required** (two-person assist = 01). |

### Activity-not-attempted codes

`07` refused · `09` not applicable (didn't perform pre-illness) · `10` environmental limitation · `88` medical condition / safety concerns.

### Coding principles

- Score by the amount of assistance actually provided.
- If performance is **unsafe or poor quality** and a helper must assist, score by that assistance.
- Assistive devices (e.g. a rolling walker) are allowed and **do not** change the code.

## Why this matters for the agent

- **Distinct tasks are not contradictions.** Ambulation (GG0170I walk), sit-to-stand / transfers (GG0170D), and bed mobility are separate activities. A patient can genuinely be **04** (supervision) to walk, **03** (moderate) to transfer, and **01** (two-person) for bed mobility. → *Marcus Bell signs clean.*
- **A real drift is a same-task contradiction.** If the note implies steady / independent gait but PT codes the *walk* task **02** (substantial/maximal), that is a genuine finding on the same activity. → *Eleanor Hayes → clarification recommended.*
- **GG scores drive money and disposition.** Section GG feeds the PDPM PT/OT case-mix and the discharge decision, so a wrong functional line affects reimbursement *and* patient safety.
