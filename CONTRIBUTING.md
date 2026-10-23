# Contributing to Q-One Core

Contributions should preserve the auditability and human boundary of the protocol.

## Before changing the protocol

- Explain the user-visible decision problem and the event or schema change.
- Preserve old event records and describe any migration.
- State what evidence the change can produce and what it cannot establish.
- Keep provider credentials and personal logs out of the repository.

## Pull requests

A pull request should include a short protocol impact note, an example payload when fields change, and the checks used to inspect the change. Do not report synthetic fixtures as real-world performance.

## Data and privacy

Use anonymized or synthetic examples in issues and documentation. The local `.qone-data/` directory is ignored by default; verify that private exports are not staged before opening a pull request.
