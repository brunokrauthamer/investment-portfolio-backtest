# USD/BRL source preparation — plan p001

Proposed against specification s001; neither revision is approved yet.

## Design and boundaries

Perform a one-time local CSV projection; no reusable scraper, service, abstraction or application dependency is needed. Read the supplied file with a CSV parser that supports quoted commas and UTF-8 BOM. Preserve the selected field text exactly, and serialize valid comma-delimited UTF-8 without BOM. Name the output as the user-supplied file to avoid inventing a new naming convention.

Use a source directory containing only the active CSV. Put provenance in `data/dolar/manifest.json`, and a temporary recovery record outside the source directory. Never overwrite a pre-existing CSV or manifest. Retain the original supplied file unchanged. Since this is an initial creation, no prior active dataset exists to back up; future updates require the project's backup, recovery, provenance and offline-restore conventions to be designed in their own task. Document the initial import and recovery procedure in `data/dolar/README.md`.

## Ordered work

1. After explicit approval of s001 and p001, record the Git baseline and worktree snapshot. Reopen the input with shared read access, compare its SHA-256 to the discovery snapshot, and validate its CSV structure and required headers. Stop on conflict or changed input.
2. Under a single developer assignment, create the CSV and provenance as staged files, prepare a write-ahead record describing their expected hashes and safe recovery, and publish each file atomically without overwriting existing files. Remove the recovery record only after both files are in place. Document origin, format, limitations and interruption recovery.
3. Obtain independent review and QA of the artifacts against the approved criteria, without adding or running tests unless the user requests testing or verification. Record any limitations, exact snapshot identity and findings. Browser scenarios do not apply to this local file preparation.
4. The lead audits the outcome and records the final approval request, as required by the workflow. The supplied download remains available for recovery; no network access is necessary.

## Risks

The input can change while another process has it open. Read a consistent byte snapshot, check its hash and stop if it differs from discovery. Decimal commas require correct CSV quoting; parsing and preserving strings avoids numeric conversion. Two files cannot be committed as one atomic operation, so a retained recovery record must make interrupted publication detectable and recoverable without clobbering unknown data. The source's terms and original retrieval time are not established.
