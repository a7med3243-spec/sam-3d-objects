---
name: claudex
description: Plan → independent review → build → independent code review, with a second "brain" checking the work. Use when the user says "claudex", e.g. "claudex this feature", "claudex this plan, mode=review, plan=docs/x.md, rounds=3", "claudex this feature, builder=codex". Options (key=value, any order) - mode=build|review|plan, plan=<path>, rounds=<n>, builder=claude|codex, reviewer=claude|codex, tests=<cmd>.
---

# claudex

A cross-checking workflow: one agent writes, a **separate, fresh-context reviewer** attacks it, and the writer must answer every finding before moving on. The reviewer never shares the writer's context, so it catches assumptions the writer can't see.

## 1. Parse the invocation

Text after `claudex` = the **subject** ("this feature", "this plan", or a description). Trailing `key=value` pairs are options:

| option | values | default |
|---|---|---|
| `mode` | `build` (plan → review → implement → code review), `review` (review an existing plan only), `plan` (plan + review, no code) | `build`; `review` if the subject says "plan" and `plan=` is given |
| `plan` | path to a plan file | `docs/plans/<slug>.md` (created) |
| `rounds` | max review rounds, 1–5 | `2` |
| `builder` | `claude` or `codex` | `claude` |
| `reviewer` | `claude` or `codex` | `claude` |
| `tests` | command to verify the build | detect from repo (package.json scripts, pytest, Makefile, CI config) |

"This feature" / "this plan" refer to what the conversation has been discussing. If nothing identifies it, ask one question — then proceed.

**Codex backends:** check `command -v codex`. If missing (or no OpenAI credentials), say so in one line and fall back to `claude` for that role. Never fake a Codex result.

## 2. Plan (mode=build|plan, or when `plan=` file doesn't exist)

Explore the code first (read the real files you'll touch). Write the plan to the plan file using this skeleton:

```markdown
# <Feature> — plan
## Goal            (1–3 sentences, user-visible outcome)
## Non-goals
## Context         (relevant files/modules with paths, current behaviour)
## Design          (approach + key decisions and why; alternatives rejected)
## Steps           (numbered, each small and verifiable, naming files)
## Risks & mitigations
## Test plan       (exact commands + new tests to add)
## Review log      (filled by the review loop)
```

## 3. Review loop (all modes)

For round = 1..`rounds`:

1. **Get an independent review.** Use the prompt in `reviewer-prompt.md` (same folder as this skill), filling in the plan path and repo root.
   - `reviewer=claude`: spawn a fresh `general-purpose` Agent (foreground; you need the result). Do not pass your own reasoning or conclusions — only the plan path, repo root, and the prompt. In round ≥2, also pass the previous Review log so it can check fixes and not repeat itself.
   - `reviewer=codex`: `codex exec --sandbox read-only -C <repo> "<filled prompt>"` and capture stdout.
2. **Triage every finding.** For each: `ACCEPT` (edit the plan) or `REJECT` (with a concrete, code-backed reason). No silent drops. Verify a finding against the code before accepting or rejecting it.
3. **Append to `## Review log`:** `### Round N — <APPROVE|REVISE>` then one line per finding: `- [sev] <finding> → ACCEPT: <change> | REJECT: <reason>`.
4. Stop when the verdict is `APPROVE` with no blocker/major findings, or `rounds` is exhausted. If exhausted with open blockers, **stop and show the user** the open items instead of building.

`mode=review` / `mode=plan` end here: report verdict, rounds used, key changes, and any open disagreements.

## 4. Build (mode=build)

- `builder=claude`: implement the steps yourself, in order, keeping the plan's Steps checklist updated (`- [x]`).
- `builder=codex`: send Codex a **self-contained** prompt (it has none of this conversation): the goal, the full plan file contents, constraints (stay in scope, no unrelated refactors, don't touch git history, run the tests), and the test command. Run `codex exec --full-auto -C <repo> "<prompt>"`. Then read the full diff yourself — you own the result.

Run the test command. Fix failures before review (max 3 attempts; then report honestly).

## 5. Code review

Get an independent review of the diff (`git diff` against the starting commit, plus new files) using `reviewer-prompt.md` with REVIEW TARGET = the diff + plan. Same backend rules as step 3. Triage findings the same way (fix or reject with reason), re-run tests. One round by default; a second only if a blocker was found.

## 6. Report

Short summary: what was built, files changed, test results (actual output if failing), review verdicts per round, findings rejected and why, anything left open. Don't commit or push unless the user asked or the repo's instructions say to.

## Rules
- Reviewer gets fresh context every time; the writer never grades its own work.
- Every finding gets a visible ACCEPT/REJECT.
- Fallbacks (codex → claude, skipped tests) are always stated, never hidden.
