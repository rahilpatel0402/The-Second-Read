# The Second Read — 2-minute demo script

**Goal of the demo:** land three beats — *catch a real error*, *stay silent when it's actually consistent*, *defend the doctor and flag the chart*. That arc proves judgment, not just detection.

## Before you present (do this every time)

1. **Pre-warm the model.** Run one full sign on any case (or `python scripts/smoke.py eleanor-hayes`) 30 seconds before you go up. This absorbs the cold-start; the live run then feels instant-ish (~13–18s).
2. Have the app already open at `http://localhost:8000` (double-click `scripts/start.bat`).
3. Start on **Eleanor Hayes**, "Clinical note" tab visible.
4. Keep the **Interdisciplinary chart** tab one click away — that's your evidence when a judge doubts the data is real.

## Cold open (say this before you touch anything — ~15s)

> "Every ambient scribe treats the doctor as the source of truth and writes down what they say. **The Second Read is the one that checks it** — against the nursing note at 10pm and the therapy note at 2pm, the ones the doctor never saw — in the half-second before the signature commits. In a skilled nursing facility, that signed note *is* the bill and *is* the care plan. Watch."

## Beat 1 — The catch (Eleanor Hayes) — ~35s

- Point out the note's line: *"ambulating in hallway with rolling walker, **steady gait**"* → *"anticipate discharge home in 5–7 days."*
- Click **Sign note**. Narrate over the modal: "It's reading the rest of the chart — PT, nursing, OT."
- Result lands: **Before you sign.** Read the split: draft on the left, and on the right PT (8 ft, maximal assist), nursing (unwitnessed fall), OT (unsafe transfers) — each **quoted with discipline + timestamp**.
- Punchline: "It flagged **only** the functional line and the discharge it drives. The incision exam and post-op day it verified and left alone — that's the difference between a check and a nuisance." Point at *verified consistent*.

## Beat 2 — The live edit (defuses "does it only work on your scripted cases?") — ~20s

- In the note textarea, **change** "steady gait" to something honest like *"requires maximal assist to ambulate, not yet discharge-ready"* and delete the 5–7 day line.
- Click **Sign note** again. This time it **signs clean**.
- "Same engine, edited note, opposite outcome — live. Nothing here is hardcoded to a script."

## Beat 3 — The silence (Marcus Bell) — ~25s

- Select Marcus Bell. Note lists three different assist levels: supervision to walk, moderate to transfer, two-person for bed mobility.
- "A naïve contradiction-checker fires here — three different numbers for 'how much help.'"
- Click **Sign note** → **signs clean**, with *"considered and cleared 1 apparent conflict."* Expand it.
- Punchline: "Those are three **distinct CMS Section GG tasks** — walking, transferring, bed mobility — and they're *supposed* to differ in a stroke with one-sided weakness. Knowing that is clinical judgment. **No false alarm** is the hardest thing to get right, and it's the whole point."

## Beat 4 — The stale record (Harold Byrne) — ~25s  *(the memorable closer)*

- Select Harold Byrne. Note: physician correctly **started apixaban** for new-onset AFib, cardiology agrees.
- Click **Sign note** → **Before you sign**, but read *who* it blames: the finding routes to **Nursing**, and *verified consistent* says the physician's reasoning, the CHA2DS2-VASc score, and cardiology are all corroborated.
- Punchline: "Here the **doctor is right and the *chart* is stale** — the MAR, hours later, still shows anticoagulation held. That's a **missed dose and a stroke risk**. The Second Read doesn't reflexively challenge the doctor — it routes the fix to whoever is actually wrong. Here, that's the record."

## Close (~10s)

> "One agent, at the signature. It catches the drift, it stays quiet when the chart is just being precise, and it defends the physician when the record is the thing that's stale. Every finding is quoted verbatim from a source document — **no quote, no finding** is enforced in code, so it structurally cannot hallucinate a challenge to a clinician."

---

## Anticipated hard questions (answer honestly, briefly)

**"Is the retrieval a real agent loop, or is it just given the whole chart?"**
> "One citation-grounded reconciliation pass — the full interdisciplinary chart goes in, and the model builds a cited ledger, reconciles per claim, routes, and drafts in a single call. We collapsed a multi-round loop into one pass on purpose: it's faster for a live signature moment and the integrity guarantee doesn't depend on retrieval — it depends on **re-verifying every quote against its source in code** (`agent.quote_in`). Anything it can't cite verbatim is dropped, not shown."

**"How do I know it isn't hallucinating the contradicting notes?"**
> "It can't surface one it can't quote. Open the **Interdisciplinary chart** tab — every quote in a finding is a verbatim span from one of these documents; the backend whitespace-normalizes and substring-checks each one before it's allowed on screen." *(Then actually open the tab.)*

**"What's the confidence score?"**
> "The model's own calibrated confidence in the finding — we surface it for transparency, not as a gate. The gate is the citation check, which is deterministic."

**"Does this only work on your three cases?"**
> "No — you just watched me edit a note live and flip the outcome. And **Import a chart** takes a native chart JSON or an Abridge FHIR record; `chart.py` normalizes it into the same shape."

**"Why the flag-to-Nursing on Harold instead of a 'stale' label?"**  *(only if a judge is deep in the output)*
> "The routing is the decision that matters — it sent the fix to the MAR owner, Nursing, and vindicated the physician in the same breath. Whether we tag that 'stale' or 'contradicted' internally, the action is correct: fix the record, not the note."

**"Where does the impact actually show up in dollars?"**
> "Section GG functional lines drive the PDPM PT/OT case-mix group that sets the SNF's daily rate, and payers reconcile the signed note against this same interdisciplinary record on audit. A functional line that contradicts therapy's coding is a denial waiting to happen. The apixaban case is the other half — that one's patient safety, not dollars."

---

## Timing cheat-sheet

| Beat | Case | Outcome | ~Time |
|---|---|---|---|
| Cold open | — | — | 0:15 |
| 1. The catch | Eleanor Hayes | Flagged | 0:35 |
| 2. Live edit | Eleanor Hayes | → clean | 0:20 |
| 3. The silence | Marcus Bell | Clean (cleared) | 0:25 |
| 4. The stale record | Harold Byrne | Flag Nursing | 0:25 |
| Close | — | — | 0:10 |

**Total ≈ 2:10.** If you're tight, drop Beat 2's re-sign but keep the *edit* — even editing without re-signing makes the "not hardcoded" point.
