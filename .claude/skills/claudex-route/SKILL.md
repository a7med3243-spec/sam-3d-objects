---
name: claudex-route
description: Decide whether a plan or change needs a second opinion (claudex review) before building, and how heavy. Use when the user says "claudex-route", or asks "should we get a second opinion / review this plan before we build?".
---

# claudex-route

Triage: recommend the **lightest** level of independent review that matches the risk. Don't run the review itself. Recommend it and give the exact command to run.

## 1. Identify the plan or change
Use the plan file the user named, or the plan or feature from the conversation. If there is none, ask one question.

## 2. Score the risk (read the relevant code and don't guess)
Add up the points for each factor that applies:

| factor | pts |
|---|---|
| Irreversible or stateful: DB or data migrations, deletes, external side effects, releases | 3 |
| Security or auth, secrets, permissions, payment, PII | 3 |
| Public API, protocol or config format changes that affect other consumers | 2 |
| Cross-cutting: more than ~5 files or more than 2 modules or packages | 2 |
| Concurrency, caching, retries, distributed state | 2 |
| Unclear requirements, or the plan has open questions or TODOs | 2 |
| Weak test coverage in the touched area | 1 |
| Unfamiliar or recently churned code | 1 |

## 3. Recommend
- **0–2: Skip.** Build directly. Normal care is enough.
- **3–5: Light.** `claudex this plan, mode=review, plan=<path>, rounds=1`
- **6–8: Full.** `claudex this plan, mode=review, plan=<path>, rounds=3`, then build with `claudex this feature, plan=<path>`
- **9+: Full plus a different model.** As above with `reviewer=codex` if the Codex CLI is available, because a different model family catches different blind spots. Otherwise use `rounds=3` with the Claude reviewer and say that Codex isn't available.

## 4. Output (keep it short)
```
Recommendation: <Skip | Light | Full | Full + Codex>   (score N)
Why: <the 2–4 factors that drove it, each with a file or plan reference>
Top questions a reviewer should press on: <1–3 bullets>
Run: <exact claudex command>
```
Then ask whether to run it now.
