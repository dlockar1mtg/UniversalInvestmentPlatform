# Phase 5.1 Certification Report

**Overall status:** PASS
**Engine version:** 5.1.10

| Gate | Status | Duration | Message |
|---|---:|---:|---|
| determinism | PASS | 0.0013s | Serialized decisions are deterministic. |
| replay | PASS | 0.0001s | Decision replay preserved all certified fields. |
| serialization | PASS | 0.0004s | Serialization passed. |
| constraints | PASS | 0.0005s | Constraints passed. |
| cross_asset | PASS | 0.0006s | Cross Asset passed. |
| regression | PASS | 0.0005s | All regression scenarios passed. |
| repository_tests | PASS | 0.5961s | Repository Tests passed. |

## Metadata

- **determinism:** `{'repetitions': 3}`
- **replay:** `{'fields_checked': 10, 'mismatches': []}`
- **serialization:** `{}`
- **constraints:** `{}`
- **cross_asset:** `{'asset_count': 4}`
- **regression:** `{'scenario_count': 3, 'failures': []}`
- **repository_tests:** `{'returncode': 0, 'output': '........................................................................ [ 34%]\n........................................................................ [ 69%]\n...............................................................          [100%]\n207 passed in 0.25s\n'}`
