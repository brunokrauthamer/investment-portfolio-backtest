## Percentage field browser validity regression

The equal-date form submission scenario was extended to assert that valid populated percentage fields leave the form valid before clicking Submit. Before the fix, `pnpm exec vitest run src/pages/ExampleChart/index.test.tsx --reporter=dot -t "offers each supported"` failed with `expected false to be true`: `HTMLFormElement.checkValidity()` returned false even with valid 25.00% shares. The JSX pattern contained an extra backslash, so the browser's built-in pattern check rejected valid decimal input.

After correcting the pattern, the same focused test passed (1 passed, 8 skipped). The complete frontend suite subsequently passed 18 tests. See `frontend-green.txt` and `frontend-typecheck-build.txt` for integrated results.
