# Milestone 1 pre-registration — first 20 resolved decisions

> Prereg v0.1 · frozen 2026-10-23 · **before** the first real decision is recorded.
> Amendments after this date must be appended as dated entries (house style), never edited in place.

## Objective

Operationalize the existing first milestone ("collect 20 resolved decisions across ≥2 low-risk domains, stable template") into a frozen, auditable protocol. This is a **data-collection gate** — no statistical inference is claimed at N=20.

## Domains (pick exactly 2 before the first decision; then freeze)

Low-risk, frequent, binary-or-short-horizon outcomes. Candidate templates:

| Domain | Example decision | Outcome horizon |
|---|---|---|
| A. 学习/工作时间分配 | 「今早已把 90 分钟投给 X 而不是 Y」→ 是否产出了可验收的 artifact | 当日/次日 |
| B. 信息与工具选择 | 「本周试用工具 T 替代现有流程」→ 是否保留/弃用 | ≤7 天 |
| C. 小额消费（≤¥200） | 「为 Z 购买 W」→ 是否达到购买时写明的用途 | ≤14 天 |

Rules: both domains must use the same decision template fields; outcome definition is written **at decision time** into the `notes` field, before any outcome exists.

## Metrics (frozen, from RESEARCH_PLAN)

1. **Protocol integrity**: event count; hash-chain `verify` passes on the frozen export; replayable state projection.
2. **Coverage**: fraction with baseline / recommendation / human-decision events (report all three denominators).
3. **Forecasting**: Brier score on rows where a success-probability and a binary outcome both exist; Wilson 95% CI; also report by domain (n per domain too small for inference — descriptive only).
4. **Missingness**: fraction with no baseline / no outcome / `unknown` / `partial`.
5. **Agency**: recommendation override rate, with qualitative reasons preserved verbatim.

## Analysis plan

- Descriptive only. No hypothesis tests at N=20; no cross-domain comparison claims.
- Frozen export + SHA-256 manifest **before** any analysis that could influence a product or paper (per RESEARCH_PLAN guardrails).
- The baseline-vs-recommendation adoption comparison stays **out of scope** for M1; it is preregistered separately only if the protocol proves stable (RESEARCH_PLAN "next loop" step 4).

## Kill / adjust criteria (declared up front)

- If >50% of decisions lack a resolvable outcome by day 30: shrink to 10 decisions, report missingness honestly, and pause before re-preregistering.
- If the decision template changes for convenience mid-window: the window restarts (template stability is the point of the gate).
- Domain pair not frozen before decision #1: the run does not count toward M1.

## What M1 is not

Not a claim that 20 observations are statistically sufficient · not a product evaluation · not a model comparison · not evidence about anyone other than the operator.
