# Usability test plan (template)

A ready-to-run moderated test with **5 participants**. Five users typically surface the most common
usability problems in a focused tool; run a second round after fixes. Fill in the bracketed fields.

## 1. Goals

1. Can state practitioners find their state's headline numbers and trend without help?
2. Do they correctly read how their state compares with the U.S., the median of states, and peers?
3. Do they understand **why** a resource is listed (the signal rule) and that it is not a recommendation?
4. Can they reach the cited source page for a resource and tell what its evidence rating means?
5. Do they notice data-quality notes and limitations before drawing conclusions?

## 2. Participants

| # | Role (recruit one or more of each) | Setting |
|---|---|---|
| P1 | State highway safety office program manager | [state / remote] |
| P2 | State or local health department injury epidemiologist | |
| P3 | State DOT safety engineer or HSIP analyst | |
| P4 | EMS / trauma system coordinator | |
| P5 | Community or advocacy organization staff | |

Screener: works on traffic safety or injury prevention at least monthly; has not used this tool.
Session: 45 minutes, remote with screen share, think-aloud. Incentive: [describe or "none"].

## 3. Setup

- App URL: [APP_URL] (or `make app` locally); site URL: [Pages URL].
- Start each session on the app with the sidebar visible, and the state picker set to a state that is
  **not** the participant's own.
- Recording consent obtained; note-taker present; timer running per task.

## 4. Script

**Introduction (3 min).** "We're testing the tool, not you. Please think aloud. This is an independent
portfolio project, not a government product. There are no wrong answers, and you can stop at any time."

**Warm-up (2 min).** "Without clicking anything, what do you think this tool is for?"

### Tasks

| # | Task prompt (read verbatim) | Success criteria | Max time |
|---|---|---|---|
| T1 | "Switch the tool to your state. How many people died in traffic crashes there in the most recent year shown?" | Selects state; states correct count and year | 2 min |
| T2 | "Is your state's fatality rate per 100,000 residents higher or lower than the U.S. rate? By about how much?" | Correct direction; approximate values from KPI or table | 2 min |
| T3 | "Which states does the tool treat as your state's peers, and how were they chosen?" | Names ≥3 peers; mentions rurality/VMT per capita (caption or Methods) | 3 min |
| T4 | "Look at pedestrian deaths over time. Describe the trend since 2014." | Picks measure in Trend; describes direction correctly | 3 min |
| T5 | "Pick one item under 'What the data suggest looking at.' Explain why the tool flagged it." | States the rule: measure, comparator (median of states), and window | 3 min |
| T6 | "Find a resource related to that signal and open the page of the source document it cites." | Opens the linked PDF page; source matches card | 3 min |
| T7 | "What does the rating on that resource mean, and who assigned it?" | Reads the verbatim rating definition; attributes it to the source (NHTSA/FHWA), not the tool | 2 min |
| T8 | "In the Action library, find roadway-design resources for pedestrians." | Uses filters (element or prevention level + topic); lists ≥2 relevant entries | 3 min |
| T9 | "Is there anything about the data for your state that should make you cautious?" | Mentions a data-quality note (e.g. unknown restraint use, EMS time completeness, small counts) | 2 min |
| T10 | "Does this tool tell your state what it should do?" | Answers no; refers to the description/disclaimer | 1 min |

**Probes (use sparingly):** "What did you expect to happen?", "What would you do next?", "How
confident are you in that answer (1-5)?"

### Post-test (8 min)

1. System Usability Scale (SUS), 10 standard items, 5-point scale.
2. "How likely would you be to use this in your work? Why?" (1-5 + open)
3. "What, if anything, would you not trust? Why?"
4. "What is missing for your job?"

## 5. Metrics and targets

| Metric | How measured | Target |
|---|---|---|
| Task success rate | Per task: success / partial / fail (criteria above) | ≥ 80% success on T1, T2, T5, T6, T10 |
| Time on task | Start of prompt to stated answer | Within max time for ≥ 4 of 5 participants |
| Errors | Wrong state, wrong comparator, misattributed rating | ≤ 1 per participant on T2/T5/T7 |
| Comprehension of signal logic | T5 correct explanation | ≥ 4 of 5 |
| Attribution of evidence | T7 attributes rating to source | 5 of 5 (critical) |
| Non-advice understanding | T10 | 5 of 5 (critical) |
| SUS | Standard scoring (0-100) | Mean ≥ 70 |
| Confidence | Post-task 1-5 | Median ≥ 4 |

Any failure on T7 or T10 is a **critical** finding: it means the tool could be read as giving advice
or rating evidence itself, so fix it before further testing.

## 6. Analysis and reporting

- Log observations in a sheet: participant, task, outcome, time, quote, issue, severity
  (0 = none, 1 = cosmetic, 2 = minor, 3 = major, 4 = critical).
- Group issues by screen (sidebar, snapshot KPIs, trend, comparison, signals, library, methods).
- Report: top 5 issues by severity × frequency, task success table, SUS, and recommended design
  changes (for the tool, not for states).

## 7. Ethics and data

No personal data beyond role and consent are collected. Recordings are deleted after analysis.
Participants are told that the project is independent and not affiliated with CDC, NHTSA, FHWA, or
USDOT.
