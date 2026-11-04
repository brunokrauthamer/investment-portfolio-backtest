# Daily returns in reais — plan p001

Status: proposed for approval, based on specification s001. No implementation is approved.

## Architecture and interfaces

Introduce a focused `daily_returns` service under `backend/src/market_data_normalizer/`, alongside the existing gathering service. Expose `generate_daily_returns_reais(data_dir=None)`, returning the generated output path. Default to the repository `data` directory independently of the caller's working directory. Read `normalized/gathered_data.csv` and all direct `*.csv` files under `dolar/source/`, interpreting `DD.MM.YYYY` and decimal-comma prices; reject duplicate dates across files and require at least one currency CSV. Ignore nested backup/staging paths. Keep parsing/validation, return calculation, and atomic publication focused within the service; reuse existing helpers only where their actual contracts match. No generic adapter or external dependency is planned.

Validate the input before publication; process dates in chronological order and retain previous nonmissing observations according to the agreed financial rules. Publish a complete CSV using a temporary sibling and atomic replacement. One derived output has no source provenance manifest. Existing source data safety and provenance remain untouched.

## Ordered work

1. Present s001/p001 and obtain explicit approval of both revision identifiers and their hashes. Capture baseline Git/worktree state before implementation.
2. Delegate one bounded TDD implementation pass to the configured developer, including meaningful regression cases for each acceptance criterion and gaps, example calculations, malformed input and publication failure. Implement the service and generated project CSV; update usage and architecture documentation.
3. Obtain an independent integrated review on the actual snapshot, address findings within the feature-workflow round limits, and independently QA each criterion and applicable regressions. Record evidence and snapshots before/after each evaluation. Browser QA is not applicable to this local backend service.
4. Audit criteria, documentation, untouched source inputs and final evidence on the same snapshot; request final human approval under the feature workflow.

## Verification and risks

Use the repository backend virtual environment and offline, isolated input fixtures for focused and existing normalizer checks. The environment is currently absent and must be created and dependencies installed from `backend/requirements.txt` before Python verification. Include the 2011 examples, missing observations in each series, currency gaps and staggered starts. Verify that intervening FX changes are included when S&P resumes and that an S&P date with missing currency uses the preceding available rate. Check the actual project output against source data without external requests. Check failure atomicity and default-root behavior. No rounding beyond standard CSV serialization is prescribed. Browser testing is not applicable.

Integrated invocation from the repository root:

```powershell
.\backend\.venv\Scripts\python.exe -c "from backend.src.market_data_normalizer.daily_returns import generate_daily_returns_reais; print(generate_daily_returns_reais())"
```
