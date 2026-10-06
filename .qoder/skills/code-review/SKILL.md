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

There is rarely **one** active change, so resolve the source before reading it. `openspec list --json` is the mechanical starting point: it returns every non-archived change with `status`, `completedTasks` / `totalTasks`, and `lastModified` — use it rather than eyeballing the directory.

Resolution order:

1. A change name the user passed.
2. A change name referenced in a commit message.
3. `openspec/changes/<change-name>/` — read `proposal.md`, `design.md`, `specs/**/spec.md`, `tasks.md`. If `list --json` shows more than one non-archived change, **do not pick one by inference**: the diff's file paths may disambiguate, and if they do not, ask.
4. If nothing resolves, ask the user where the spec is. If they say there isn't one, the **Spec** sub-agent skips and reports "no spec available".

#### 2a. freshness gate — run this before handing the spec to the sub-agent

A spec is a fact source only while the code agrees with it. An unverified stale one is worse than none: the sub-agent will report legitimately evolved code as scope creep, and report unbuilt requirements as missing. So for the resolved change:

- **Reject a parked change as the originating spec.** `status: in-progress` with `completedTasks: 0` (or a `proposal.md` banner saying 未实施 / backlog) means the change is *designed but not started* — it is a plan, not the thing this diff implements. Such a change may be named as "the work this diff did *not* do", never as a list of missing requirements. Watch for the compounding case: a parked change whose `tasks.md` points at the repo's hottest files (for this repo: the `deduct_stock` / `lock_stock` / `ship_stock` trio in `inventory_service.py`) will silently attach a dozen phantom findings to *any* diff touching them.
- **Check each decision the diff touches against the code, not just against the text.** `design.md` entries are written as present-tense decisions (`决策：主库切 PostgreSQL`) whether or not they landed, so skim reads them as fact. Before judging fidelity, confirm the named symbol, column type, path, or route actually matches; `grep` the identifier the decision mandates and look at what the code says, including comments — a code comment stating a different deliberate choice (`凭证号沿用单据号体系：JV-YYYYMMDD-XXX`) is a live conflict, not an oversight.
- **A dated correction supersedes only the text it replaces.** When an entry carries a correction that says it supersedes earlier wording, quote only the corrected version; never let the superseded sentence lead, because it usually sits first and still reads as live. Reporting the stale half *is* the misjudgment. If the stale sentence is still physically present where a skim will hit it, report that as a finding against the spec itself: superseded text should be struck, not annotated in place.
- **Where spec and code disagree, downgrade the verdict.** Emit `## Conflict` — "both sides claim authority; which one wins is an unrecorded decision" — rather than (a) missing-requirement or (b) scope-creep. Either side may be correct, and an invented verdict here costs more than an open question.
- **Compare against the current-truth layer too.** `openspec/specs/<capability>/spec.md` holds what a capability was when its change was archived; an in-flight delta holds what a change wants it to become. If the diff's capability has a main spec and the two disagree, report that as `## Conflict` as well — and note that a capability can have been re-implemented by a *later* change whose deltas live under a different namespace, in which case the archived main spec is the older truth and should be re-synced.

Record what the gate consumed (change name, `completedTasks/totalTasks`, which decisions were code-checked) so the next review can tell a verified source from an assumed one.

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
- The outcome of the 2a freshness gate: which decisions were confirmed against the code, and which are already known to conflict. Pass this down as a constraint, not as background — without it the brief below will happily convert stale text into findings.
- The brief: "Report: (a) requirements the spec asked for that are missing or partial — check every `tasks.md` item and every requirement in `specs/**/spec.md`, but only for a spec source that passed the freshness gate; a parked change contributes nothing here; (b) behaviour in the diff that wasn't asked for (scope creep) — this verdict is available **only** for a requirement the gate confirmed the spec still asserts, never for a decision entry carrying a dated correction or a code comment that contradicts it; (c) requirements that look implemented but where the implementation looks wrong. Quote the spec line for each finding. Add a `## Conflict` section for spec-vs-code disagreements flagged by the gate and put nothing in (a) or (b) that depends on resolving one. Under 400 words."

If the spec is missing, skip the Spec sub-agent and note that in the final report.

### 5. Aggregate

Present the two reports under `## Standards` and `## Spec` headings, verbatim or lightly cleaned. Do **not** merge or rerank findings, because the two axes are deliberately separate.

Carry the Spec axis's `## Conflict` items out as their own heading, separate from both. A conflict is not a Spec finding with a softer label and not a Standards violation: it is an unrecorded decision, and folding it into either axis turns a question the repo cannot answer into a verdict it did not earn. Each conflict gets one line stating which two artefacts disagree, quoted from both sides, and the decision needed to close it.

End with a one-line summary: total findings per axis, the worst issue _within each axis_ (if any), and the count of open conflicts. Don't pick a single winner across axes: that's the reranking the separation exists to prevent.

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
