# E01 MM Autonomous Execution Queue

## Purpose

This queue wraps the existing first-cooldown binding workflow with file-backed orchestration.
It does not replace the authoritative branch spec, measurement protocol, analysis protocol, or run-binding JSON.

The queue owns:

- queue state,
- validator outcomes,
- lease ownership,
- retry accounting,
- escalation reasons,
- detection of as-run evidence,
- scheduler-style one-shot processing,
- append-only audit snapshots.

The queue does not own:

- branch classification,
- falsifier logic,
- analysis ordering,
- scientific interpretation.

## Execution-Sheet Synchronization Contract

The execution sheet is a downstream operator artifact derived from the authoritative run-binding JSON.
It is never treated as a source of truth for queue state or reconciliation.

Synchronization rules:

- only write fields that are already bound in `run_binding`,
- preserve unresolved operator placeholders such as `UNBOUND` and `TBD`,
- skip writes when reconciliation has conflicts, stop conditions are active, or validator severity is blocking,
- permit conservative sync in pre-run and as-run states once the queue item has reached `READY_FOR_PRECHECK` or later,
- support previewing proposed sheet edits without mutating the sheet.

`sheet_sync` contains at least:

- `status`
- `synced_at`
- `updated_fields`
- `skipped_fields`
- `reason_codes`

## Queue Manifest Contract

Each queue item is a JSON file containing:

- `queue_item_id`
- `branch_slug`
- `cooldown_id`
- `queue_state`
- `run_binding_path`
- `execution_sheet_path`
- `required_evidence_paths`
- `retry_count`
- `max_retry_count`
- `last_validator_result`
- `escalation_reason`
- `lease_owner`
- `lease_acquired_at`
- `lease_expires_at`
- `reconciliation`
- `sheet_sync`
- `run_binding`

`run_binding` is the embedded payload of record and mirrors the linked run-binding JSON on each worker tick.
`reconciliation` stores the last evidence-ingestion outcome, populated fields, missing fields, conflicts, and source summaries.
`sheet_sync` stores the last execution-sheet synchronization outcome, including updated fields, skipped fields, and structured reason codes.

## Runner Contract

The queue runner scans a queue directory for queue manifest JSON files, processes each manifest once, and exits.
This mode is intended for Task Scheduler or cron style automation rather than a resident process.

Runner rules:

- skip items with an active unexpired lease owned by another worker,
- reclaim expired leases,
- persist queue manifests and authoritative run-binding JSON after each processed item,
- write append-only audit snapshots under an audit directory,
- return process exit `0` for normal item-level blocked, failed, or escalated outcomes,
- return nonzero only for runner-level failures.

## Audit Snapshot Contract

Each audit snapshot is a JSON file containing at least:

- `snapshot_version`
- `queue_item_id`
- `worker_id`
- `processed_at`
- `queue_state_before`
- `queue_state_after`
- `reconciliation`
- `last_validator_result`
- `escalation_reason`
- `run_binding_path`
- `queue_manifest_path`
- `outcome`

Snapshots are append-only.
If two snapshots would collide on timestamp-derived filenames, the runner must uniquify the later filename rather than overwrite the earlier snapshot.

## Queue States

- `QUEUED`: manifest exists but has not entered validation.
- `READY_FOR_PRECHECK`: waiting for automated pre-run validation.
- `BLOCKED_MISSING_BINDING`: missing pre-run fields or provenance references.
- `READY_FOR_HARDWARE`: pre-run plan is valid and awaiting physical cooldown execution.
- `IN_PROGRESS`: at least one as-run evidence path now exists.
- `READY_FOR_AS_RUN_BINDING`: the run-binding payload has switched to `AS_RUN_BINDING`.
- `BLOCKED_VALIDATION`: as-run validation found retryable gaps.
- `COMPLETE`: all as-run binding requirements passed.
- `FAILED`: terminal structural failure.
- `ESCALATED`: stop condition or non-discriminating outcome requires human review.

## Automated Transition Rules

1. `QUEUED -> READY_FOR_PRECHECK`
   Automatic on first worker tick.
2. `READY_FOR_PRECHECK -> READY_FOR_HARDWARE`
   Requires the pre-run validator to pass.
3. `READY_FOR_PRECHECK -> BLOCKED_MISSING_BINDING`
   Triggered by missing hardware identifiers, witness binding, selected fields, dwell schedule, or provenance references.
4. `READY_FOR_HARDWARE -> IN_PROGRESS`
   Triggered when any declared or bound as-run output path exists on disk.
5. `IN_PROGRESS -> READY_FOR_AS_RUN_BINDING`
   Triggered when `run_binding.binding_context == AS_RUN_BINDING`.
6. `READY_FOR_AS_RUN_BINDING -> COMPLETE`
   Requires all as-run provenance, calibrated settings, output paths, and binding checks to pass with `binding_status == AS_RUN_BOUND`.
7. `READY_FOR_AS_RUN_BINDING -> BLOCKED_VALIDATION`
   Triggered by retryable evidence gaps such as missing provenance paths, missing output paths, or uncalibrated `P_read`.
8. `READY_FOR_AS_RUN_BINDING -> ESCALATED`
   Triggered by explicit stop-condition reason codes.
9. `READY_FOR_AS_RUN_BINDING -> FAILED`
   Triggered by malformed queue or run-binding payloads.

## Reason Codes

Common blocking reasons:

- `MISSING_HARDWARE_BINDING`
- `MISSING_WITNESS_CHANNEL`
- `MISSING_MATCHED_GEOMETRY_BINDING`
- `MISSING_FIELD_PROGRAM`
- `MISSING_SELECTED_FIELDS`
- `SELECTED_FIELDS_NOT_SUBSET`
- `PROBE_SCHEDULE_LENGTH_MISMATCH`
- `MISSING_PROVENANCE_PATH`
- `PROVENANCE_PATH_NOT_FOUND`
- `OUTPUT_PATH_NOT_FOUND`
- `P_READ_NOT_CALIBRATED`
- `AS_RUN_BINDING_NOT_ACTIVE`
- `MISSING_REQUIRED_SOURCE_FIELD`

Escalation reasons:

- `NON_DISCRIMINATING_STOP`
- `SHAM_CONTROL_MISSING`
- `WITNESS_CHANNEL_MISSING`
- `BASELINE_DRIFT_OUT_OF_TOLERANCE`
- `FIELD_RETURN_CHECK_FAILED`
- `FIELD_CALIBRATION_UNTRUSTED`

Reconciliation reasons:

- `SOURCE_PARSE_FAILED`
- `SOURCE_CONFLICT`
- `MISSING_REQUIRED_SOURCE_FIELD`
- `UNSUPPORTED_SOURCE_FORMAT`
- `RUN_BINDING_WRITE_SKIPPED`

Sheet synchronization reasons:

- `SHEET_SYNC_SKIPPED`
- `SHEET_SYNC_CONFLICT`
- `SHEET_SYNC_PARSE_FAILED`
- `SHEET_SYNC_WRITE_SKIPPED`

## Worker Usage

Create a queue manifest from the authoritative run-binding JSON:

```powershell
python execution_queue/e01_mm_execution_queue.py create `
  --queue-item-id e01_mm_cd001 `
  --run-binding-path protocols/e01_mm_first_cooldown_run_binding.json `
  --execution-sheet-path protocols/e01_mm_first_cooldown_execution_sheet.md `
  --output-path execution_queue/e01_mm_first_cooldown_queue_manifest.json
```

Advance one manifest:

```powershell
python execution_queue/e01_mm_execution_queue.py tick `
  --manifest-path execution_queue/e01_mm_first_cooldown_queue_manifest.json `
  --worker-id codex_worker
```

Advance every queue item in the directory once:

```powershell
python execution_queue/e01_mm_execution_queue.py tick-directory `
  --queue-dir execution_queue `
  --worker-id codex_worker
```

Run scheduler-friendly discovery once and write audit snapshots:

```powershell
python execution_queue/e01_mm_execution_queue.py run-once `
  --queue-dir execution_queue `
  --worker-id codex_worker
```

Preview reconciled updates without writing files:

```powershell
python execution_queue/e01_mm_execution_queue.py reconcile-dry-run `
  --manifest-path execution_queue/e01_mm_first_cooldown_queue_manifest.json
```

The dry-run output includes the proposed reconciled run-binding payload and the proposed execution-sheet text.
