# USD/BRL source preparation — specification s002

## Goal and scope

Prepare the user-supplied Investing.com CSV as `data/dolar/source/USD_BRL Dados Históricos (1).csv`. Keep only `Data` and `Último`, renaming the latter `price`. This is a one-time preparation of the supplied file.

The supplied input inspected during discovery is UTF-8 with a BOM, has headers `Data,Último,Abertura,Máxima,Mínima,Vol.,Var%`, and contains 4,132 records. Its SHA-256 is `0fa13625511a444b282e7626eef081c8408896213191687580428dbd33ccf3a7`. Dates use `DD.MM.YYYY`; prices use a decimal comma. The observed records run from 03.11.2026 to 03.01.2011 in their original order. Treat these observations as a snapshot, not a promise about any later input.

## Acceptance criteria

- **AC-001 — Exact projection:** Read the supplied CSV as CSV, including quoted values and the accented `Último` header. Produce exactly two columns in order, `Data` and `price`, with one output record for every input record. Preserve each selected field's text and input order, including decimal precision; do not sort, deduplicate, convert dates or prices, or synthesize data. Quote fields as required for a valid comma-delimited CSV.
- **AC-002 — Destination and encoding:** Save the CSV at the path stated above, using UTF-8 without BOM, consistent with the project's generated Selic CSV. The B3 original CSVs use a different encoding; they are preserved source downloads. Leave the supplied download unchanged.
- **AC-003 — Safety and provenance:** Treat an existing destination or provenance file as a conflict and stop without overwriting it. Stage output before publishing it. Keep a write-ahead recovery record until both the active CSV and a matching `data/dolar/manifest.json` have been committed, using atomic file replacement for each. Record the supplied file name and hash, the output hash and record count, the Investing.com page URL, the local transformation and schema, and the fact that the original retrieval time and usage terms are unverified; do not invent them. Document recovery from an interrupted initial import. Do not include backups as active inputs.
- **AC-004 — Boundaries:** No network request, scraper, return calculation, financial transformation, dependency or backend command is introduced. An unavailable, changed, malformed or unexpectedly structured input must stop without publishing partial or misleading data.

## Decisions and limits

The source snapshot was supplied by the user; the specified URL identifies its stated origin and is not evidence of its retrieval time or a grant of redistribution rights. This task does not settle market-data alignment, financial interpretation, or future update behavior. A changed input after discovery requires a fresh read and a recorded decision before publication.

## Follow-up context: scraper

After preparing the CSV, the user intends to start a new Beautiful Soup scraper. Its stated goal is to access `https://br.investing.com/currencies/usd-brl-historical-data`, find dates absent from the CSV, and add only the date (`Data`) and price (the source's `Último`, stored as `price`). This is context for subsequent work, not an approved design or acceptance criterion for this preparation task. Scraper implementation and its detailed behavior remain outside the present scope.
