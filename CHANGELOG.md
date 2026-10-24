# Changelog

## 0.2.0 — 2026-10-24

- Added transactional DecisionService and finite-number/timezone/schema validation.
- Added concurrent baseline and transition tests.

## Unreleased

- Fixed forecast scoring to exclude recommendations whose option was not selected.
- Added traceable eligible rows, exclusion reasons, and explicit adoption denominators.
- Added seven regression tests including a synthetic CLI flow and an override case that fails on the original implementation.
- Fixed optional empty text validation so resolving a decision without notes works.

- Added source-linked Chinese research synthesis and implementation priorities.
- Clarified prototype status and pending real-model acceptance.

## 0.1.0 — 2026-10-23

- Added the first decision schema and example.
- Added a local append-only JSONL ledger with a SHA-256 hash chain.
- Added baseline, recommendation, human decision, outcome, and abandonment events.
- Added human-review gates and evidence-aware aggregate reports.
- Added the three-repository blueprint and initial research plan.
