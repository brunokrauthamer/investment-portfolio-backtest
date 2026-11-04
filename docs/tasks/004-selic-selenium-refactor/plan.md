# Selic Selenium refactor — plan p001

Status: proposed 2026-11-03, paired with specification s001; awaiting explicit human approval of both revisions before implementation.

## Architecture and boundaries

Keep `selic/source.py` responsible for source browser lifecycle, interaction and validation, returning its existing `SourceResult`/`Observation` contract. Replace the Playwright-specific adapter internals with Selenium WebDriver for headless Chrome and use bounded explicit waits for the chart iframe, refresh, navigation and page content. Confirm successful refresh and page transitions from the actual browser interaction and response evidence where needed to avoid accepting stale content; if those signals are unavailable or ambiguous, fail safely. Use a small injectable driver boundary to exercise browser interactions without network. Always quit the driver, including on errors. Keep import-time behavior inert. Retain existing validation helpers wherever appropriate.

Continue using the existing service, registry, storage and restoration boundaries; only adapt integration interfaces where actually necessary. Declare Selenium in the backend requirements and remove Playwright/greenlet only after checking other uses. Selenium Manager can locate a matching driver when needed, or a compatible browser/driver can be installed locally; document the actual setup and first-run network implications. See [Selenium Manager](https://www.selenium.dev/documentation/selenium_manager/) and [Selenium waits](https://www.selenium.dev/documentation/webdriver/waits/).

## Ordered execution

1. Record baseline HEAD, worktree status and deterministic snapshot, including pre-existing changes. In the first bounded developer pass, follow feature-tdd for the Selenium browser interaction, waits, cleanup, metadata, pagination and failure handling. Adapt the existing browser tests to Selenium while preserving independent validation and storage tests. Update the requirements and affected current documentation.
2. Run the relevant offline getter suite and appropriate checks using `backend/.venv`; record actual evidence and the integrated snapshot. Independently review the approved criteria, implementation, existing behavior, documentation, dependencies and snapshot. Address confirmed defects with observed failing regressions using the workflow's remaining rounds.
3. Independent QA checks all criteria, adverse cases and regression evidence on the same snapshot. It performs the live Selenium source workflow with a temporary data directory and compares BCB table samples and count to the produced CSV. This is a backend CLI acquisition feature; there is no new user-facing web interface. Record a blocked live criterion if access or browser execution fails.
4. Audit review, QA, documentation, current snapshot and unresolved findings. Request final approval only after required independent checks pass; retain any blocker and its evidence.

## Risks and alternatives

Selenium and Chrome/driver versions must be compatible. Selenium Manager may require network access for first-time driver resolution. BCB's asynchronous refresh, paginated table, metadata and access availability can change; bounded waits, successful refresh/navigation evidence, strict identity/range/count checks and live comparison guard against stale or incomplete data. Source values can change between pages without a count change, which may not be detectable. The direct data API is outside the user's chart-scraping request. No changes to project data are needed for verification.
