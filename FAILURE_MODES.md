# Failure modes

These limits are properties of the code in this repository. They are not an attacker playbook, and they are not fixed by calling `qone verify`.

`qone verify` and `Ledger.verify` recompute each event hash and check `seq` and `prev_hash`. A one-byte edit that leaves the stored hash unchanged makes `verify` fail. That is the detection this ledger actually implements.

## Hash chain, forks, and tampering

The chain has no signature, no published tip hash, and no external witness. Anyone who can write the file can produce another file that `verify` accepts.

- **Rehashed suffix.** Change an earlier payload, recompute that event's hash, and recompute `prev_hash` and `hash` for every later event. `verify` returns success. The tests in `tests/test_ledger_limits.py` build that file and observe a successful verify.
- **Truncated prefix.** Delete the later lines and leave a prefix whose own hashes still match. `verify` reports the shorter file as valid. It cannot tell that events were removed.
- **Fork.** Copy a prefix into two files and append different events. Each file verifies. Nothing in this repository compares the two tips.
- **Whole-file replacement.** Replacing `ledger.jsonl` with a different well-formed chain also verifies. There is no anchor outside the file.
- **Writer lock.** `Ledger._lock` uses `fcntl.flock` when `fcntl` imports. That is a local advisory lock on one machine. The Windows import fallback takes no lock. The lock is not a seal, and it does not bind a copy of the file.

A retained copy of an old tip hash, kept outside the ledger file, would make a rewritten tail detectable by comparison. This repository does not store or check such a tip.

## Trusted import: `Ledger.append`

`DecisionService` is the product API. Each method calls `Ledger.transact`, which holds the writer lock, verifies the current chain, checks the projected state, and then appends one event. A second baseline, a recommendation before a baseline, and a decision from the wrong status raise `ValidationError` without adding an event. `decide` always stores `decided_by` as `human`.

`Ledger.append` is a trusted-import primitive. It verifies the chain and writes the payload it was given. It does not apply product transitions. Observed consequences, covered by `tests/test_writer_boundary.py`:

- A recommendation can be appended with no baseline.
- A second baseline can be appended. The projection keeps the later baseline.
- A recommendation can be appended before the baseline. The projection then shows `baseline_recorded` and still retains the earlier recommendation.

The CLI is not `DecisionService`. `src/qone_core/cli.py` checks some transitions in the command handler, then calls `Ledger.append`. Those checks run before the lock, and `append` does not repeat them. Two concurrent CLI writers can therefore both pass a check that `DecisionService` would allow only once. `decide --by` stores the string it is given, including a value that is not `human`.

`validate_recommendation` sets `requires_human` true and `auto_eligible` false. `check_recommendation` refuses only a missing baseline. Low confidence, high risk, irreversibility, and `personal_calibration_n` below 20 are recorded as `gate_reasons` and the recommendation is still stored. No command in this repository executes the chosen option.

## Baseline gaming

A baseline event is evidence that a writer appended that payload, in that order, in that file. It is not evidence that a person chose the baseline before seeing a recommendation.

- The writer can choose the baseline to match a recommendation they have already seen, then append the baseline first. The chain is valid. The file does not record when the person saw the recommendation.
- `Ledger.append` can write the recommendation first and the baseline second. Later readers of the projection still see both.
- Reports compare stored fields. They do not correct a baseline that was selected to look good after the fact. Adoption and Brier figures move with those fields. `build_report` labels the result descriptive and excludes recommendations whose option was not the human choice. That exclusion does not stop someone from choosing the baseline, the recommendation, and the outcome so the scored subset looks calibrated.

Synthetic life-kernel, calibration, recency, and two-scale artifacts in this repository are frozen numeric experiments. They are not a user study, and they do not authorize an automatic recommendation.
