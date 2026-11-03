# IBOVESPA daily-evolution acquisition — plan p001

Status: proposed 2026-11-03 against specification s001; awaiting explicit human approval of both revisions.

## Architecture and choices

Add `backend/src/internet_data_getter/ibovespa/` with source adapter for B3's actual annual download and validation, service for annual orchestration/reporting, local store for provenance, exclusive lock, atomic updates and recovery, and CLI reporting/restore. Register the getter and commands in the existing shared registry, so default all-getters and explicit selection discover it. Keep `acquire_ifix` and existing `restore` compatibility. Expose an unambiguous IBOVESPA-specific restore command without conflicting with IFIX's existing `restore`; finalize its spelling in documentation and tests.

The existing IFIX source and storage boundaries are the behavioral reference, not an excuse to change IFIX semantics. Reuse or extract shared implementation only where the real two-asset requirement justifies it and behavior remains covered. Avoid a speculative provider framework. Data and locks stay asset-specific; the existing data root and module registry remain the assembly boundaries. Standard library is preferred; add a backend dependency only if verified source mechanics require it and document why.

## Ordered work and evidence

1. **Source gate:** Inspect actual B3 IBOV page/download mechanics, earliest and current-year annual responses and applicable access restrictions. Establish actual endpoint, index code, original filename, encoding, transport, structure and validation, without assuming the linked page route itself is the CSV endpoint. If unavailable, record the blocker; if incompatible with s001, return for a human decision.
2. **Implementation round, test first:** Assign the configured developer the approved revisions and sole implementation/verification writer token. Record failing tests before implementation and passing results for the IBOV source, service, registry, CLI and storage. Cover each acceptance criterion and relevant IFIX regressions with controlled non-market fixtures. Continue yearly processing on errors, return a truthful incomplete report, and keep imports network-free.
3. **Data safety and docs:** Verify identical files, changed files, backups, manifest validation and write-ahead recovery, interruption, offline restore, per-asset locking, and cross-asset isolation. Update relevant getter/data docs with run, limitations, provenance and recovery procedures. Obtain real files only through explicit invocation, preserving source bytes and the user's data.
4. **Independent review and QA:** Review the integrated snapshot against s001/p001, including existing IFIX regressions. Independent QA exercises every criterion, real-source earliest/current-year comparisons and the documented CLI when source access permits. This is a CLI feature; a browser test of a project UI is not applicable, though source inspection may use a browser. Record evidence and snapshot freshness. Follow the workflow's bounded review/correction rules.
5. **Final audit:** Run `./backend/.venv/Scripts/python.exe -m unittest discover -s backend/src/internet_data_getter/tests` on Windows and relevant CLI help/integration checks. Audit documentation, findings and evidence on the final snapshot. Request explicit final human approval; do not commit, push or deploy merely on that approval.

## Risks

B3 may change the format, withhold an annual file, or return an error with HTTP 200; validate content and report incomplete. The current year can be partial or initially have no observations; IFIX-equivalent validation treats a file without any observations as incomplete. Shared-code changes could regress IFIX, and restore subcommands could collide; test both assets and keep existing interface compatibility. Backups and write-ahead recovery carry data-safety risk and require failure injection. Source access or external restrictions may block live QA; never infer a pass from mocks.
