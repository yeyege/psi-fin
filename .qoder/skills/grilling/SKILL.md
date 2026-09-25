---
name: grilling
description: Grill the user relentlessly about a plan, decision, or change before implementing. Use when the user wants to stress-test their thinking, uses any 'grill' trigger phrase, or a change is being designed for this WMS/finance system and its decisions are not yet all settled. Distinct from openspec-explore, which diverges; this one converges until nothing is silently assumed.
---

Interview the user relentlessly until you reach a shared understanding. Map this as a **design tree**: every decision branches into the decisions that hang off it.

Work the tree in **rounds**. The **frontier** is every decision whose prerequisites are already settled: the questions you can ask _now_ without guessing at answers you haven't heard yet. Ask the whole frontier in one round: number each question and give your recommended answer. Then wait for the user's answers before the next round.

Format a round like so:

```
❓ **Q1** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>

---

❓ **Q2** - **<question title>**: <question body, might be multiple paragraphs, including multiple choices>

➡️ <your recommended answer>
```

Each round the user answers reshapes the tree: settled decisions push the frontier outward and unblock questions that depended on them. Recompute the frontier and ask the next round. A question whose answer depends on another question still open in this round belongs to a _later_ round, not this one.

## Before the first round

Read these so the questions are asked in the project's own language and against its real constraints:

- `.qoder/repowiki/knowledge/zh/业务术语表/业务术语表.md` — the domain vocabulary. Use its terms (`available_qty`/`locked_qty` 分离, 防超卖, 会计内核, 波次拣货, CamelModel 契约) rather than paraphrasing them.
- `AGENTS.md` — the hard rules. A decision that would violate one is not an open question; say so and ask the user to re-scope. Read §1–§4 fresh from the file rather than recalling them from this skill: nothing here restates them, because a copy in two places is the drift `AGENTS.md` §6 forbids.
- `openspec/changes/<change-name>/` if a change is already in flight — read `proposal.md` and `design.md` so you do not re-ask what is already settled.

## Find facts, don't ask for them

Finding _facts_ is your job, never the user's. When a frontier question needs a fact from the environment (filesystem, code, DB schema, running tests), dispatch a sub-agent to find it; don't ask the user for anything you could look up yourself. Don't block on it: a running exploration is an unsettled prerequisite, so only the questions downstream of it wait for the sub-agent to report; ask the rest of the frontier now. The _decisions_ are the user's: put each to them and wait.

## Branches this repo always owes

A change touching these areas is not settled until each named branch has an answer. Ask the branch, not the general worry.

| Area | Question the frontier must settle |
|---|---|
| 库存变动 | 走 `inventory_service.add_stock`/`deduct_stock` 吗？`FLOW_TYPE_*` 用哪个？流水在哪个事务边界写入？ |
| 并发扣减 | 需要 `SELECT ... FOR UPDATE` 吗？注意单测的 SQLite 会静默忽略它，MySQL 8.0 与 PostgreSQL 才真的加行锁——你观察到的行为是哪个方言给出的？ |
| 状态机 | 新状态还是新动作？动作走子资源路径（`/api/inbound-orders/{id}/receive`）还是被塞进请求体？ |
| 金额 | 已定案，不是开放问题：一律 `Numeric(18,2)` + `Decimal`，经 `app/common/money.py` 的 `money()` 量化（ROUND_HALF_UP），比较用精确相等，见 `AGENTS.md` §4。要问的只有两件：① 本次改动是否新增金额列需要跟进 Alembic 迁移（`create_all` 不会 ALTER）？② 若边界值会因舍入口径变化（存量 `.xx5` 值差 1 分），业务上接受吗？ |
| 接口契约 | 返回 `code` 200 还是 201？列表要不要 `{list,total,page,pageSize}`？排序字段是什么？ |
| 跨模块 | 只经 service 层调用，还是直接改别人的表？ |
| 前端 | 走 `CamelModel` camelCase 契约吗？错误经 Axios 拦截器还是自己 catch？ |

## Completion criterion

The session is done when the frontier is empty: every branch of the design tree visited, nothing left silently assumed. Do not act on it until the user confirms you have reached a shared understanding.

A very long session usually means the scope was too big — say so plainly and propose splitting the change rather than pushing through the remaining rounds.

## Where the answers land

Once confirmed, hand the settled tree to the spec stage rather than letting it evaporate from context: point the user at `/opsx:propose` (or, if a change already exists, offer to write the decisions into its `design.md`). Do not open a second source of truth for the same decision.
