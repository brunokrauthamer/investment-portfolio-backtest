# Plan p001: Multiple portfolio results

Approved specification: s001. Workflow: simple-feature-workflow.

1. Update `frontend/src/services/portfolio.ts` with typed Axios response handling and runtime validation of the agreed single-series contract, preserving a valid empty array.
2. Update the existing `ExampleChart` page state and submission flow to capture immutable submitted configurations, generate UI-only identifiers, stable labels and colors on success, append retained results, and reset the form only after valid success. Derive series and removable cards from those entries. Keep the form's existing validation and pending behavior.
3. Adapt reusable chart options and UTC formatting in `chart.ts`, style the cards and states in `index.css`, and remove production example series and example-only UI. Retain direct x/y mapping and no financial calculations. Update the frontend README for the actual frontend behavior and current backend prerequisite.
4. Use meaningful test-first evidence and focused frontend verification for success, repeated submissions, reset and snapshots, removal and stable identity, pending, error, invalid and empty responses, direct point mapping, UTC handling, and absence of examples; run relevant frontend tests and typecheck/build. An independent reviewer reviews the integrated result, with at most one developer fix pass, then independent QA exercises acceptance criteria and browser behavior using test-only API doubles where needed. The current backend supports only acknowledgement/error-path verification until it is updated.

The user approved this plan with `Approve and proceed` on 2026-11-04 (America/Sao_Paulo). No commit, push, merge or deployment is authorized by this task.
