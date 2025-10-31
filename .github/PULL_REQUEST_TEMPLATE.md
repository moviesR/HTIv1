## Summary
<!-- What changed and why? Link issues. -->

## Checklist
- [ ] `system_slice.yaml` validated; `physics_hash` current
- [ ] Soak tests (10 min) pass: no misses; p99 ≤ caps
- [ ] Probe hygiene (TTL/refractory/≤2-before-action) passes
- [ ] Shield last-writer + TTL expiry tests pass
- [ ] EventPack ±300 ms window + required fields present
- [ ] If probabilities touch Control: calibration (ECE/Brier) + conformal gates pass
- [ ] Docs updated (README/CONTRIBUTING) if behavior/limits changed
