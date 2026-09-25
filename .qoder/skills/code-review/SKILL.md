---
name: code-review
description: Two-axis review of the diff since a fixed point — Standards (does it follow AGENTS.md plus a Fowler smell baseline?) and Spec (does it faithfully implement the originating openspec change?). Runs both as parallel sub-agents so neither pollutes the other. Use when the user wants to review a branch, a PR, or work-in-progress changes, or asks to "review since X".
---

Two-axis review of the diff between `HEAD` and a fixed point the user supplies:

- **Standards**: does the code conform to this repo's documented coding standards?
- **Spec**: does the code faithfully implement the originating openspec change?

Both axes run as **parallel sub-agents** so they don't pollute each other's context, then this skill aggregates their findings.

## Process

### 1. Pin the fixed point

Whatever the user said is the fixed point (a SHA, branch name, tag, `main`, `HEAD~5`). If they didn't specify one, the default is **the uncommitted work in the current working tree** — that is what an agent just wrote, and it is the most common thing to review.

Capture the diff once, branching on the target:

| Target | Commands |
|---|---|
| Uncommitted work (default) | `git status --porcelain -uall` then `git diff HEAD` |
| A committed range | `git diff <fixed-point>...HEAD` (three-dot, so the comparison is against the merge-base) and `git log <fixed-point>..HEAD --oneline` |

`git diff HEAD` does **not** show untracked files: when the change set includes new files (it usually does — new routers, new services, new tests), either `git add -N <paths>` first, or read each untracked file listed by `status -uall` in full.

Confirm here, before spawning sub-agents, that the target resolves (`git rev-parse <fixed-point>`) and that **both** the diff and the untracked list are empty-false. An empty working tree with nothing untracked should fail now, not twice, in parallel — say so and ask for a fixed point rather than reviewing nothing.

### 2. Identify the spec source

In this order:

1. A change name the user passed.
2. `openspec/changes/<change-name>/` for the branch's active change — read `proposal.md`, `design.md`, `specs/**/spec.md`, `tasks.md`.
3. A change name referenced in a commit message.
4. If nothing resolves, ask the user where the spec is. If they say there isn't one, the **Spec** sub-agent skips and reports "no spec available".

### 3. Identify the standards sources

**`AGENTS.md` at the repo root is the primary source.** Its rules are hard, not advisory, and it is unusually load-bearing here because the repo has **no linter and no type checker on the Python side** — no ruff, no mypy, no eslint. Only `vue-tsc` runs, via `npm run build`. So the conventions below are enforced by nothing but this review; do not assume the agent's code was checked.

**This skill deliberately does not restate those rules.** `AGENTS.md` §6 says: when it and a skill disagree, fix `AGENTS.md`, and do not copy a rule set into each skill. A pasted copy is already known to drift (it once claimed `FOR UPDATE` only works on PostgreSQL, while MySQL 8.0 honours it just fine). So the Standards sub-agent reads `AGENTS.md` §1–§4 itself; the table below only says which clause to hold against which shape of diff:

| Diff looks like | Clause to check |
|---|---|
| Route function touching `db.query` / doing validation inline | §1 四层架构 |
| Stock movement not through `inventory_service`, or no `inventory_flows` row | §2 库存不变量 |
| Partial write on failure, hand-rolled order numbers | §2 事务与单号 |
| Response envelope, status codes, list shape, sorting | §3 统一响应 |
| Missing auth dependency, extra state field in a body | §3 鉴权与契约 |
| Money type / rounding / comparison, and whether a column change came with an Alembic revision | §4 金额与迁移 |
| Concurrency or locking evidence produced only on SQLite | §4 单测方言陷阱 |

If a rule in `AGENTS.md` is genuinely unenforceable from a diff, that is a bug in `AGENTS.md` — report it, don't work around it here.

On top of the repo's own rules, the Standards axis always carries the **smell baseline** below — a fixed set of Fowler code smells (_Refactoring_, ch.3) that applies even where a repo documents nothing. Two rules bind it:

- **The repo overrides.** A documented standard always wins; where it endorses something the baseline would flag, suppress the smell.
- **Always a judgement call.** Each smell is a labelled heuristic ("possible Feature Envy"), never a hard violation.

Each smell reads *what it is* → *how to fix*; match it against the diff:

- **Mysterious Name**: a name that doesn't reveal what it does or holds. → rename it; if no honest name comes, the design's murky.
- **Duplicated Code**: the same logic shape in more than one hunk or file. → extract the shared shape, call it from both.
- **Feature Envy**: a method reaching into another object's data more than its own. → move the method onto the data it envies.
- **Data Clumps**: the same few fields or params keep travelling together. → bundle them into one type, pass that.
- **Primitive Obsession**: a primitive or string standing in for a domain concept deserving its own type. → give the concept its own small type.
- **Repeated Switches**: the same `switch`/`if`-cascade on the same type recurs. → polymorphism, or one map both sites share.
- **Shotgun Surgery**: one logical change forces scattered edits across many files. → gather what changes together into one module.
- **Divergent Change**: one module edited for several unrelated reasons. → split so each module changes for one reason.
- **Speculative Generality**: abstraction or hooks added for needs the spec doesn't have. → delete it; inline back until a real need shows.
- **Message Chains**: long `a.b().c().d()` navigation the caller shouldn't depend on. → hide the walk behind one method on the first object.
- **Middle Man**: a class or function that mostly just delegates onward. → cut it, call the real target direct.
- **Refused Bequest**: an implementer that ignores or overrides most of what it inherits. → drop the inheritance, use composition.

### 4. Spawn both sub-agents in parallel

**Standards sub-agent prompt** — include:

- The diff command and commit list (plus the full text of any untracked new file).
- An instruction to read `AGENTS.md` §1–§4 **from the repo** before judging — do not paste a copy of the rules here; the copy is what drifted before. The table from step 3 may be pasted, since it only routes diff-shape to clause.
- The smell baseline from step 3, pasted in full — this one is not documented anywhere in the repo, so it has to travel.
- The brief: "Report, per file/hunk where relevant, (a) every place the diff violates a documented standard: cite the standard (file + the rule); and (b) any baseline smell you spot: name it and quote the hunk. Distinguish hard violations from judgement calls: documented-standard breaches can be hard, but baseline smells are always judgement calls, and a documented repo standard overrides the baseline. Skip anything tooling enforces. Under 400 words."

**Spec sub-agent prompt** — include:

- The diff command and commit list.
- The path or fetched contents of the openspec change.
- The brief: "Report: (a) requirements the spec asked for that are missing or partial — check every `tasks.md` item and every requirement in `specs/**/spec.md`; (b) behaviour in the diff that wasn't asked for (scope creep); (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Under 400 words."

If the spec is missing, skip the Spec sub-agent and note that in the final report.

### 5. Aggregate

Present the two reports under `## Standards` and `## Spec` headings, verbatim or lightly cleaned. Do **not** merge or rerank findings, because the two axes are deliberately separate.

End with a one-line summary: total findings per axis, and the worst issue _within each axis_ (if any). Don't pick a single winner across axes: that's the reranking the separation exists to prevent.

### 6. Run the checks

The diff is not reviewable until it is green. Per `AGENTS.md` §4:

```bash
cd backend-python; uv run pytest
cd frontend-vue; npm test; npm run build
cd frontend-vue; npm run test:e2e   # 涉及核心链路时
```

If the diff touches a model column, `AGENTS.md` §4 adds a gate the tests cannot cover: `create_all` never ALTERs an existing table, so a column change without an Alembic revision is a hard violation regardless of how green pytest is. Check for a file under `backend-python/migrations/versions/` in the diff, and that `alembic upgrade head` was actually run against a real MySQL/PostgreSQL target (see `backend-python/scripts/check_money_columns.py` for the shape of that evidence).

Report actual output, with secrets replaced by `<REDACTED>` — never paste a raw `.env` value or an auth header into the review.

## Why two axes

A change can pass one axis and fail the other:

- Code that follows every standard but implements the wrong thing → **Standards pass, Spec fail.**
- Code that does exactly what the spec asked but breaks the project's conventions → **Spec pass, Standards fail.**

Reporting them separately stops one axis from masking the other.
