# Q-One Core protocol

A decision is a bounded question with a deadline, an observable success criterion, two to eight options, and a stated reversibility and risk level. The schema is in [schemas/decision.schema.json](../schemas/decision.schema.json); runtime validation lives in `src/qone_core/models.py`.

## Event lifecycle

```text
decision_created
        |
baseline_recorded
        |
recommendation_made  -- optional
        |
human_decision
        |
outcome_recorded  -- or decision_abandoned
```

The ledger accepts events only from the fixed event-type set. A projection derives the current state from the event history instead of mutating earlier records.

## Event fields

Every event contains:

- `seq`: one-based position in the ledger
- `ts`: UTC timestamp
- `type`: one of the six protocol event types
- `payload`: event-specific JSON object
- `prev_hash`: hash of the previous event, or 64 zeroes for the first event
- `hash`: SHA-256 of the canonical event content excluding `hash`

The append path verifies the existing chain before writing. `qone verify` replays the same checks on the file it is given. It does not prove that this file is the only history, or that a writer has not rebuilt a consistent tail. Those limits are in [FAILURE_MODES.md](../FAILURE_MODES.md).

## Writers

Product transitions belong in `DecisionService`. That class holds the ledger writer lock while it checks the projected state and appends one event. `decide` stores `decided_by` as `human`.

`Ledger.append` skips those checks. It is a trusted-import primitive: the chain is verified, and the supplied payload is stored. The `qone` CLI calls `Ledger.append` after its own checks. Those checks are not inside the lock, and `decide --by` stores the argument it is given. Neither path executes the chosen option.

## Baselines and recommendations

A baseline records the option a writer says a person would choose before seeing an agent recommendation. `DecisionService.recommend` and the CLI `recommend` command require a baseline event before they append a recommendation. `Ledger.append` does not. A baseline event is a comparison point in the file. It does not prove the person had not already seen the recommendation, and it does not by itself stop a writer from replacing an earlier judgment.

Recommendations record:

- `option_id`: the proposed option
- `confidence`: preference strength in the recommendation, in `[0, 1]`
- `success_probability`: predicted probability of meeting the declared criterion, in `[0, 1]`, when the agent can justify it
- `rationale`: concise explanation tied to the criterion
- `source`: model, rule, or workflow identifier
- `gate_reasons`: conditions that keep the recommendation human-reviewed

`validate_recommendation` sets `requires_human=true` and `auto_eligible=false`. `check_recommendation` refuses only a missing baseline. Low confidence, high risk, irreversibility, and insufficient personal calibration are recorded as reasons and the recommendation is still stored. `Ledger.append` does not call either function.

## Outcomes and metrics

Only resolved `yes` and `no` outcomes for the human-selected recommended option enter the Brier-score calculation. If the human chooses another option, the recommendation's outcome is unobserved and is excluded as `recommended_option_not_selected`. `partial`, `unknown`, unresolved records, missing choices or probabilities, and invalid probabilities are also excluded. Each scored row includes a decision ID and option ID; exclusions have explicit counts and decision IDs.

`recommendation_adoption_n` counts human decisions that had a recommendation, so human-only decisions do not dilute the adoption rate. The report retains `calibration` as the JSON field name for compatibility, but Brier score is a forecast loss and is not by itself proof of calibration. The selected subset cannot establish causal improvement or outcomes of unselected options. The Wilson interval is descriptive under the binomial model; repeated personal observations may violate its independence assumptions.

These metrics describe the collected decision process. They do not establish causal effects, clinical validity, or universal human preferences.
