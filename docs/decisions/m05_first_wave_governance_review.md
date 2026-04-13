# M05 First-Wave Promotion-Adjacent Governance Review

This session executed a synthetic first-wave smoke test for `m05-case-device-specific` under request `QDPLAB-EBE5E0010DAD7DE8`.

The request pack deliberately superseded the surfaced `Single-device follow-up` schedule with `Cross-device matched-fabrication sweep` so the workflow could be exercised against the actual promotion-adjacent blocker.

## Synthetic scope

- The request-pack override is governed repo state and is suitable as a planning artifact.
- The result packet, calibration snapshot, and lineage record are synthetic smoke-test fixtures only.
- No physical lab evidence was recorded by this session.

## Observed post-ingest state

- `cross_device_status=CONFIRMED`
- `candidate_target_devices=["DEV_MATCH_A", "DEV_MATCH_B"]`
- `dataset_governance.status=COMPLETE`
- `calibration_status.status=VALID`
- `scientific_decision=PROVISIONALLY_IDENTIFIABLE_PENDING_CROSS_DEVICE_TEST`
- `governance_outcome=SANDBOX_ONLY`
- `promotion_cap_governance=SANDBOX_ONLY`

## Comparison to the confirmed reference

`m05-case-confirmed-proceed` already carries `cross_device_status=CONFIRMED`, `scientific_decision=CROSS_DEVICE_CONFIRMED_IDENTIFIABLE`, `governance_outcome=PROCEED`, and no governance cap.

The updated `m05-case-device-specific` ingest result now matches the confirmed reference on cross-device evidence, calibration validity, and dataset governance, but it does not match on the cap and decision layer. The surviving blocker is not missing evidence inside the ingest packet. The surviving blocker is retained governance state.

## Decision

- The cap remains in force under current implementation and policy.
- This session does not authorize a cap reset.
- Any promotion-path continuation now requires a separate decision: either preserve `SANDBOX_ONLY` as the intended terminal state for this branch, or implement and approve a cap-reset policy that is explicitly keyed to confirmed cross-device evidence rather than assumed by ingest.
