# Verification

## Implementation round 1 — spec s002, plan p002

The source was reopened with shared read access and its SHA-256 matched the approved discovery snapshot: `0fa13625511a444b282e7626eef081c8408896213191687580428dbd33ccf3a7`. The local CSV parser confirmed the expected headers and 4,132 source records. The projection retained the two selected source field values in their original order.

The output was staged with a write-ahead record and published only after checking that the destination and manifest did not exist. Both active files matched their staged hashes before the pending record and staging directory were removed.

Manual artifact inspection found:

- CSV: `data/dolar/source/USD_BRL Dados Históricos (1).csv`; strict UTF-8 decoding succeeded, no BOM was present, and the file contains 4,133 lines including the header `Data,price`.
- First and last observations remain in the source order: `03.11.2026,"5,4900"` and `03.01.2011,"1,6465"`.
- CSV SHA-256: `b43e448cdd88c22cf4690c1803cf3c96c4778e03d0ae3dd8c2c43dd2e7f68169`; this matches `manifest.json`.
- Manifest SHA-256: `4ded5cb557101b8042e513fbaf14e75aef3ee37a0e22e3a7308aef4c8fc67438`.
- No pending import record or staging directory remains. The supplied download was only read.

No automated tests were added or run; this is a one-time data artifact preparation and the user did not request tests. Independent review and QA remain outstanding. Snapshot: [implementation-snapshot.json](evidence/implementation-snapshot.json).

## Independent QA — initial round 1 — spec s002, plan p002

**Assessment: passed for the approved data artifact.** Read-only inspection was performed on 2026-11-04 (America/Sao_Paulo) against snapshot `e322d90ff4d70fc3561b0ddb7510ade64bbcc589:sha256:a3ec5e02675212570a1b3e5fc06c363389d5b7e461a3ad4046339d4c0bf318c5`. Before and after QA snapshots matched. The supplied input hash still matches the discovery hash and the manifest. The source download was not modified.

| Criterion | Expected | Actual |
| --- | --- | --- |
| AC-001 | Two columns `Data,price`; one row per source record; preserve selected text and order. | Parsed source and output independently with quoted comma handling. All 4,132 output rows matched the source's first two values in order. The output header is exactly `Data,price`; no row mismatches. Pass. |
| AC-002 | Approved path; UTF-8 without BOM; leave source unchanged. | Output exists at the approved path, decoded as strict UTF-8, and has no BOM. Its SHA-256 is `b43e448cdd88c22cf4690c1803cf3c96c4778e03d0ae3dd8c2c43dd2e7f68169`, matching the manifest. Source hash is `0fa13625511a444b282e7626eef081c8408896213191687580428dbd33ccf3a7`, matching discovery and manifest. Pass. |
| AC-003 | Matching provenance, no fabricated retrieval or usage claims, and a documented safe initial-import recovery path. | Manifest fields and hashes agree with the files; retrieval time and usage terms remain explicitly unverified. README describes the pending record, staging directory, conflict handling, and offline recovery. The active source directory contains only the CSV; the pending record and staging directory are absent after publication. The publication sequence and intermediate hash checks are recorded in the developer handoff; QA inspected the published state and docs but did not replay the write sequence or simulate interruptions, since this task has no executable updater and no tests were requested. Pass for the artifact and documentation, with that execution limitation. |
| AC-004 | No network activity, scraper, financial calculation, extra dependency, or backend command. | The integrated snapshot differs from baseline only by the CSV, manifest, and README; no code or dependency changes were introduced. The scraper remains follow-up context. Pass. |

No browser scenario applies to this local file preparation. No tests were added or run. The independent artifact observations are in [qa-initial-1-artifacts.json](evidence/qa-initial-1-artifacts.json); matching before/after repository identities are in [qa-initial-1-before.json](evidence/qa-initial-1-before.json) and [qa-initial-1-after.json](evidence/qa-initial-1-after.json). The review independently passed with no actionable findings in [review.md](review.md).

## Lead final audit — 2026-11-04 (America/Sao_Paulo)

The approved s002/p002 hashes, review, QA and all four acceptance results refer to the same product snapshot. There are no recorded open findings or active assignments. The [final repository snapshot](evidence/final-snapshot.json), generated using the workflow's read-only snapshot script, matches the reviewed and QA-assessed snapshot. Documentation consists of the dataset README and provenance manifest. No tests were added or run; the one-time write sequence and interrupted recovery were not replayed. Final human approval of the completed snapshot remains pending.
