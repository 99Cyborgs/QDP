## Summary

- describe the user-facing or engineering change
- list the main modules touched

## Validation

- [ ] `ruff format --check .`
- [ ] `ruff check .`
- [ ] `mypy src`
- [ ] `pytest`
- [ ] `mmm-studio run-demo --profile broadband --top-n 5 --output-dir artifacts/pr-smoke`

## Notes

- note any optional dependency considerations
- note any intentionally deferred work or remaining risks
