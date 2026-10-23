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

The append path verifies the existing chain before writing. `qone verify` replays the same checks.

## Baselines and recommendations

A baseline records the option a person would choose before seeing an agent recommendation. The baseline is required before an agent recommendation can be recorded. This gives later analysis a comparison point and prevents the agent from silently replacing the user's original judgment.

Recommendations record:

- `option_id`: the proposed option
- `confidence`: preference strength in the recommendation, in `[0, 1]`
- `success_probability`: predicted probability of meeting the declared criterion, in `[0, 1]`, when the agent can justify it
- `rationale`: concise explanation tied to the criterion
- `source`: model, rule, or workflow identifier
- `gate_reasons`: conditions that keep the recommendation human-reviewed

The current gate always sets `requires_human=true` and `auto_eligible=false`. Low confidence, high risk, irreversibility, and insufficient personal calibration are recorded as reasons for additional caution.

## Outcomes and metrics

`yes` and `no` outcomes are the only binary labels used for the initial Brier-score calculation. `partial` and `unknown` remain in the ledger but are excluded from that calculation. The report also gives a Wilson interval for the observed binary success rate when there are eligible rows.

These metrics describe the collected decision process. They do not establish causal effects, clinical validity, or universal human preferences.
