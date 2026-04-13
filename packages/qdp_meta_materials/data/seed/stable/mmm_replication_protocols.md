# MMM Replication Protocols

## Claim maturity ladder
| Tier | Requirement | Output state |
| --- | --- | --- |
| R0 | Single device, single cooldown, detectability passed | screening only |
| R1 | >=3 devices and >=2 cooldowns with same sign | repeatable same-design effect |
| R2 | >=2 fabrication batches or >=2 device classes | portable branch effect |
| R3 | Portable plus geometry scaling plus null closure | validated mechanism candidate |
| R4 | Cross-lab or independent foundry replication | program-level publication claim |

## Mandatory replication rules
- Replicate on at least two cooldowns for every promotable result.
- Use the same analysis code path across batches and device classes.
- Carry package identifiers and metrology hashes into the dataset manifest.

## Cross-device matrix
See `mmm_cross_device_registry.yaml` for required device/substrate/batch combinations.
