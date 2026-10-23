# Three-repository blueprint

The project is intentionally split so that the measurement contract can remain stable while model adapters and personal interfaces evolve independently.

## 1. q-one-core

Core owns the decision schema, event types, hash-chain ledger, gate rules, and evidence-aware aggregate reports. It should remain provider-neutral and runnable offline. A core release must preserve old event records and document schema migrations.

## 2. q-one-agent

Agent owns model selection, prompting, tool calls, retrieval, and evidence adapters. It may call local models or hosted models, including adapters inspired by Laya/Jev-style workflows, but it must emit a core-compatible recommendation with source, confidence, rationale, and captured evidence references. Provider credentials and raw private context stay outside the core repository.

## 3. q-one-life

Life owns a user-facing ontology for areas such as health, learning, work, relationships, finance, and recovery. It provides review workflows and integrations while keeping the core event contract intact. Personal data should be stored locally or in an explicitly selected private store, with redaction and export controls.

## Dependency direction

```text
q-one-life  ->  q-one-agent  ->  q-one-core
                         \----->  model/provider adapters
```

The arrow means “depends on the contract.” The core repository does not depend on a provider or on a UI. This makes it possible to replace models without changing the measurement history.

## Release order

1. Freeze and document the core event contract.
2. Build agent adapters that can replay a decision without sending private data by default.
3. Add the personal ontology and review UI after the first two layers have stable interfaces.
