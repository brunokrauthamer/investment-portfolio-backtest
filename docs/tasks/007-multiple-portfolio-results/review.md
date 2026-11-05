# Review

## Independent review

Specification s001, plan p001; reviewed snapshot `9635e616d1e274383a4c3b4f049251dce6ba8624:sha256:ed3d3023fd77693424cf15364cce0783579516ebb2c132e48dc5e0a02a3e3262`. Verdict: changes requested. Reviewer made no edits; suite, typecheck, build and browser checks remain blocked by absent dependencies.

- R1 (P1): `index.test.tsx:282,288,302` expects IBOVESPA 100% after deselecting only IFIX, leaving three indexes selected; expected actual share is 33.34%. Unscoped `getByText("6 months")` is ambiguous between option and card. Fix setup or expected value and scope assertions.
- R2 (P1): `interop.test.tsx:11-13` expects the chart to mount immediately, but the new initial empty state does not mount it; adapt the regression to submit a valid response before asserting wrapper compatibility.
- R3 (P2): `chart.ts:52-54` rounds colors to RGB without checking collisions. Reviewer reproduced identical `#3c9a1d` for portfolios 7 and 384 using a local Node probe. Ensure newly assigned colors differ from those already allocated and remain readable/stable; add focused coverage beyond the first 40.

## Single developer fix pass

Developer reports R1 corrected by selecting only IBOVESPA and scoping card assertions; R2 corrected by submitting a valid response before asserting wrapper rendering; and R3 corrected by tracking all assigned colors and seeking unused candidates, including after removal. A new test covers 1,024 sequential colors. A Node probe of the candidate algorithm reported 1,024 distinct colors, including distinct values for positions 7 and 384. `git diff --check` passed; Vitest, typecheck and build remain blocked by absent local binaries and EACCES on prior package retrieval. Fixed snapshot: `9635e616d1e274383a4c3b4f049251dce6ba8624:sha256:efa014b3414e3d3f6ce75fb041872d597c71e95c73ab1aebf0be6135810f2009`. Findings have not received a second review; QA assesses the integrated result directly.
