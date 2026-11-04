# S&P 500 acquisition plan — p001 (proposal)

Status: proposed; not approved. Proposed against specification s001.

## Responsibilities and flow

1. Extend the existing getter registry and CLI with `sp500`; add a dedicated `fetch-sp500 --start-date YYYY-MM-DD --end-date YYYY-MM-DD` command and `acquire_sp500(data_dir=None, start_date=None, end_date=None)` Python entry point. Normal `--getter sp500` and all-getters invocation use defaults. Place source, service, CLI and storage responsibilities together in `backend/src/internet_data_getter/sp500/`.
2. Source code builds explicit inclusive calendar intervals, converts each to UTC Unix bounds, fetches the authorized `^GSPC` page with normal HTTPS verification, and parses confirmed daily table columns using BeautifulSoup. It returns typed observations and provenance only after validating each interval. Provider errors, uncertain empty pages and evidence of truncation stop the transaction. Do not claim that a page proves the provider never omitted a row; no external trading calendar is approved.
3. A service holds the asset lock, validates/recoveries the current CSV and provenance, computes earlier and later missing ranges and the one-date latest overlap, requests and validates all needed windows, merges by date under AC-006, then asks storage to commit. It reports added/updated counts and requested windows. No network activity occurs on import.
4. Storage serializes validated values and owns the paired backup, manifest, write-ahead record, atomic replacement, recovery and offline restore. Follow the existing Selic safety model, including hash checks and stale-lock handling. Share generic storage helpers only where their contracts genuinely fit both sources; do not couple the S&P 500 to Selic's provenance or data format.
5. Update dependency manifest, acquisition and project documentation including Yahoo access/usage constraints, exact command examples, record formats, backup/restore and the limits of incremental history. Avoid speculative finance or UI changes.

## Ordered work and dependencies

- The user stated they have Yahoo's express prior permission for automated collection. Discovery fetched the supplied page without bypassing access controls and observed its first/last dates and table row count. If the method or desired data changes, revise and reapprove the affected spec and plan.
- Present concrete s001/p001 for explicit human approval, recording exact content hashes. No implementation starts before approval.
- Record baseline HEAD and worktree status. Dispatch one bounded developer pass under the approved revisions, covering source/parser/date conversion, increment/merge, transactional storage/restore, integration, documentation, and appropriate offline verification. Follow feature-tdd evidence and the single-writer handoff protocol to the extent permitted by higher-priority session instructions.
- Have a separate reviewer examine the integrated snapshot against all criteria and architecture; route findings within workflow round limits. Then have independent QA assess the approved criteria, adverse cases, offline restore and existing-getter behavior on the same snapshot. This backend acquisition feature has no user-facing browser flow; the source website is not the product UI.
- Audit documentation and final evidence, enforce snapshot freshness, and request final human approval. Corrections follow the workflow's bounded cycle; no commit, push, publication or scheduled collection is implied.

## Verification scenarios

Use controlled HTML response fixtures and temporary directories; include inclusive date and timezone boundary cases, complete multi-year HTML, historical truncation/pagination and malformed field responses, recognized empty intervals, current-day correction, duplicate dates, earlier backfill, incremental suffix, narrower ranges, provider/HTTP errors, manifest tampering, interrupted writes, backup hash failures, restore, concurrent lock and unchanged reruns. Verify no live network on imports or offline restore. Run the getter suite from the repository root using `backend/.venv` where the current higher-priority instructions allow it. Record actual commands, observations, environment, source-access limits and all unrun checks. A real authorized source observation is a separate integration check and is not replaced by fixtures.

## Risks

Yahoo's terms require prior permission for automated collection, which the user stated they have; its HTML or access rules can change. The observed long-range page included both requested endpoints where observations were available, but does not prove every observation was present. Current-day values may change, and one-date overlap intentionally leaves earlier corrections undetected. Transactions involving both CSV and provenance require recovery evidence for every interruption point. Restores must retain the restored version's provenance. The chosen local-calendar default and UTC query boundaries are explicit proposed conventions, not market-alignment rules.
