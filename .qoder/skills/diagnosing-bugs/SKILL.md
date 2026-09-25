---
name: diagnosing-bugs
description: "Diagnosis loop for hard bugs and performance regressions in this WMS/finance system. Use when the user says \"diagnose\"/\"debug this\", or reports something broken, throwing, failing, wrong-numbered, or slow. Phase-gated: no hypothesis until a red-capable feedback loop exists."
---

# Diagnosing Bugs

A discipline for hard bugs. Skip phases only when explicitly justified.

When exploring the codebase, read `.qoder/repowiki/knowledge/zh/业务术语表/业务术语表.md` for the module map in the project's own vocabulary, `AGENTS.md` for the invariants the bug may have already broken, and the relevant `openspec/changes/<name>/specs/**/spec.md` for what the behavior was supposed to be.

## The dialect trap — check this first

This repo runs on **three different SQL dialects**, and `SELECT ... FOR UPDATE` behaves differently in each. Most "impossible" concurrency and inventory bugs here are this:

| Environment | Dialect | `FOR UPDATE` |
|---|---|---|
| `uv run pytest` 单测 | SQLite (`tests/conftest.py` 临时库) | **silently ignored** |
| `npm start` / 直接 `uvicorn app.main:app`（未设 `DATABASE_URL`） | SQLite（`backend-python/psi_fin.db`，见 `app/database.py`） | **silently ignored** |
| `docker compose up` 本地联调 | MySQL 8.0 | effective |
| 线上真后端演示：Vercel Serverless + Neon | PostgreSQL | effective（`render.yaml` 只是备选 Blueprint） |

So a 防超卖 or 行级锁 bug **cannot reproduce under the unit suite**, and a test that passes does not prove the invariant holds. Before hypothesising, state which dialect the observation came from, and refuse to treat a green SQLite run as evidence about locking. Reproduce against MySQL or PostgreSQL if the bug is about concurrency.

The same asymmetry applies to column types: `Numeric(18,2)` is stored as REAL by SQLite and is only enforced for real on MySQL/PostgreSQL. A money figure that looks right on SQLite is not evidence the schema is correct — that is what `backend-python/scripts/check_money_columns.py` is for.

## Redact

This skill shows commands, outputs, and captured artifacts. **Redact every secret first**: write `<REDACTED>` in its place. `docker-compose.yml` and `.env.example` carry credentials — build loops against env vars, so the credential stays in the environment rather than in what you show. Quote only the lines carrying the signal.

If the redacted output is not enough to diagnose the bug, say so and ask.

## Phase 1: Build a feedback loop

**This is the skill.** Everything else is mechanical. If you have a **tight** pass/fail signal for the bug (one that goes red on _this_ bug), you will find the cause; bisection, hypothesis-testing, and instrumentation all just consume it. If you don't have one, no amount of staring at code will save you.

Spend disproportionate effort here. **Be aggressive. Be creative. Refuse to give up.**

### Ways to construct one, in roughly this order for this repo

1. **Failing pytest at a service seam** — `cd backend-python; uv run pytest tests/test_<area>_service.py`. The service layer is where the invariants live, so this is usually the highest-value loop. Run one file, not the suite, to keep it fast.
2. **Two concurrent callers in one test** for anything locking- or transaction-related — one caller per test cannot exercise 防超卖. Against SQLite this proves nothing about `FOR UPDATE` (see the dialect table).
3. **HTTP script against the dev server** — `curl` the FastAPI route, asserting the full `{code,message,data}` envelope and the exact symptom, not "didn't 500". Inject `DATABASE_URL` first: with it unset, the dev server is talking to SQLite and the loop stays on the wrong dialect no matter how real it looks.
4. **SQL probe on the real DB** — `docker compose exec mysql mysql -u<user> -p<redacted> psi_fin -e "SELECT ..."` to compare `inventory_flows` against stock totals (the table is plural; a `Table doesn't exist` here is your own typo, not a missing flow row). Money- and stock-invariant bugs are usually found by a reconciliation query, not by reading Python.
5. **Playwright E2E** — `cd frontend-vue; npm run test:e2e` when the bug only appears through the real request/UI chain.
6. **Vitest unit** — `cd frontend-vue; npm test` when the wrong number is computed client-side, which in this repo means the Mock/Pages 演示层 aggregates only; real 账龄分桶与驾驶舱数字是服务端 `finance_service` 算的（走回路 1）。
7. **Replay a captured trace** — save the real request payload / response to disk and replay it through the service function in isolation.
8. **Throwaway harness** — spin up one service with mocked deps and drive the suspect path with a single call.
9. **Property loop** — for "sometimes wrong" money or stock math, run many random orders through and watch for the invariant to break.
10. **Bisection harness** — if the bug appeared between two known commits, wire `git bisect run` to loop 1.
11. **HITL bash script** — last resort, when only a human can click. Drive them with [scripts/hitl-loop.template.sh](scripts/hitl-loop.template.sh) so the loop stays structured; captured output feeds back to you. The script is bash-only (`set -euo pipefail`, `printf -v`, interactive `read`), so on this Windows repo it must be run by the user in Git Bash/WSL from their own terminal — the agent's shell has no stdin to answer its prompts.

Tighten the loop once you have one: can I make it **faster** (one test file, one test id, skip unrelated fixtures), sharper (assert the user's exact symptom, not "no exception"), more **deterministic** (pin time, seed RNG, isolate the DB file, freeze network)? A 30-second flaky loop is barely better than no loop; a 2-second deterministic one is a debugging superpower.

### Non-deterministic bugs

The goal is not a clean repro but a **higher reproduction rate**. Concurrency bugs in this repo are the common case: loop the trigger 100×, parallelise, add stress, narrow the timing window, inject sleeps — and note that SQLite may remove the contention entirely, so move dialect before you conclude it can't be reproduced. A 50%-flake bug is debuggable; 1% is not.

### When you genuinely cannot build a loop

Stop and say so explicitly. List what you tried. Ask the user for: (a) access to whatever environment reproduces it, (b) a redacted captured artifact (failing request/response pair, SQL dump showing the flow-vs-stock discrepancy, log excerpt, screen recording with timestamps), or (c) permission to add temporary instrumentation. Do **not** proceed to hypothesise without a loop.

### Completion criterion: a tight loop that goes red

Phase 1 is done when the loop is **tight** and **red-capable**: you can name **one command** that you have **already run at least once** (show the invocation and its output, redacted) and that is:

- [ ] **Red-capable**: drives the actual bug code path and asserts the **user's exact symptom**, so it can go red on this bug and green once fixed. Not "runs without erroring".
- [ ] **Deterministic**: same verdict every run (flaky: a pinned, high reproduction rate).
- [ ] **Fast**: seconds, not minutes.
- [ ] **Agent-runnable**: unattended, a human in the loop only via `scripts/hitl-loop.template.sh`.
- [ ] **Right dialect**: for anything locking- or transaction-related, run on MySQL or PostgreSQL, and say which.

If you catch yourself reading code to build a theory before this command exists, **stop: jumping straight to a hypothesis is the exact failure this skill prevents.** No red-capable command, no Phase 2.

## Phase 2: Reproduce + minimise

Run the loop. Watch it go red as the bug appears. Confirm:

- [ ] The loop produces the failure mode the **user** described, not a nearby failure. Wrong bug = wrong fix.
- [ ] Reproducible across runs (or at a high enough rate, for flaky bugs).
- [ ] The exact symptom captured (error message, wrong quantity, wrong balance figure, timing) so later phases can verify the fix addresses _it_.

Then **minimise**: cut inputs, callers, config, data, and steps **one at a time**, re-running after each cut, keeping only what is load-bearing. Done when removing any remaining element makes the loop go green. A minimal repro shrinks Phase 3's hypothesis space and becomes Phase 5's regression test.

Do not proceed until you have reproduced **and** minimised.

## Phase 3: Hypothesise

Generate **3–5 ranked hypotheses** before testing any. Single-hypothesis generation anchors on the first plausible idea.

Each must be **falsifiable**:

> "If <X> is the cause, then <changing Y> will make the bug disappear / <changing Z> will make it worse."

If you cannot state the prediction, it's a vibe: discard or sharpen.

For this system, weigh the recurring causes first: 流水与库存不同源（某条路径绕开了 `inventory_service` 唯一入口）、事务边界错位（部分明细已提交）、`FOR UPDATE` 被方言吞掉、可用量与锁定量算混、浮点参与金额比较、单号重试路径吞掉了真实异常、状态机动作未走子资源路径。

**Show the ranked list to the user before testing.** They have domain knowledge that re-ranks instantly, or know hypotheses already ruled out. Cheap checkpoint, big time saver. Don't block on it; proceed with your ranking if the user is AFK.

## Phase 4: Instrument

Each probe maps to a specific prediction from Phase 3. **Change one variable at a time.**

1. **Debugger / REPL inspection** if the environment supports it. One breakpoint beats ten logs.
2. **Targeted logs** at the boundaries that distinguish hypotheses.
3. Never "log everything and grep". Note that this repo has no logging framework — it uses bare `print`, so instrument deliberately and clean up completely.

**Tag every debug log** with a unique prefix, e.g. `[DEBUG-a4f2]`. Cleanup then becomes a single grep. Untagged logs survive; tagged logs die.

**Perf branch.** For performance regressions, logs are usually wrong. Establish a baseline (timing harness, profiler, `EXPLAIN` query plan — remember the dialect table when reading a plan), then bisect. Measure first, fix second.

## Phase 5: Fix + regression test

Write the regression test **before the fix**, but only if there is a **correct seam** for it.

A correct seam exercises the **real bug pattern** as it occurs at the call site. If the only available seam is too shallow (single-caller test when the bug needs multiple concurrent callers; SQLite test when the bug is lock behavior), a regression test there gives false confidence.

**If no correct seam exists, that itself is the finding.** The codebase architecture is preventing the bug from being locked down. Flag it.

If a correct seam exists:

1. Turn the minimised repro into a failing test at that seam.
2. Watch it fail.
3. Apply the fix.
4. Watch it pass.
5. Re-run the Phase 1 loop against the original, un-minimised scenario.

## Phase 6: Cleanup

Required before declaring done:

- [ ] Original repro no longer reproduces (re-run the Phase 1 loop)
- [ ] Regression test passes (or absence of a correct seam is documented)
- [ ] All `[DEBUG-...]` instrumentation removed (`grep` the prefix)
- [ ] Throwaway prototypes deleted (or moved to a clearly-marked debug location)
- [ ] The full gates are green: `uv run pytest`, and `npm test; npm run build` if the frontend was touched
- [ ] The hypothesis that turned out correct is stated in the commit message, so the next debugger learns
