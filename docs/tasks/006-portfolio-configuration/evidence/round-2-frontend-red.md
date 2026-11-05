# Round 2 frontend regression tests — red

With the round 1 implementation unchanged, `pnpm exec vitest run src/pages/ExampleChart/index.test.tsx src/pages/ExampleChart/contrast.test.ts --reporter=dot` failed the four new regressions:

- **PC-R01:** After entering 40% for IBOVESPA, blurring, then entering and blurring 50% for IFIX, the committed IBOVESPA share was 25 but its displayed field still read 40. The test expected 25 and observed 40.
- **PC-R02:** After entering 101% in IFIX and submitting the form, Axios was called once with the previous 25/25/25/25 allocation. The regression expected zero requests and an alert blocking submission.
- **PC-R05:** Allocation guidance contrast measured 3.89155:1 (required 4.5:1), and keyboard focus contrast measured 1.85296:1 (required 3:1).

The remaining 12 tests in those two files passed in the same run.
