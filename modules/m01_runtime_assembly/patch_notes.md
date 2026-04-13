# M01 Runtime Assembly Patch Notes

- Adds a real M01 runtime-assembly module that records runtime provenance, recovery-vs-authoritative lane assignment, and a closure report.
- The module is provenance-aware: reconstructed surrogate retained bodies keep M01 in recovery-interim status even when the runtime prompt is present.
- This does not claim independently recovered retained-source authority.
