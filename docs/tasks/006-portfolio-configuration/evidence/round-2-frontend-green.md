# Round 2 frontend regression tests — green

After the PC-R01 through PC-R02 fixes, `pnpm exec vitest run src/pages/ExampleChart/index.test.tsx src/pages/ExampleChart/contrast.test.ts --reporter=dot` passed all 16 tests in those two files.

- The PC-R01 sequence now displays `25, 50, 12.5, 12.5` after the second change and blur, matching the committed allocation and 100% total.
- For PC-R02, submitting while a 101% draft remains focused makes no Axios request and leaves the invalid field alert visible. On blur, the input restores the committed share.
- PC-R05 guidance contrast is at least 4.5:1 and focus contrast is at least 3:1 against the white card.

The final full frontend suite passed 22 tests across five files. Typecheck and production build passed; the existing chart bundle size warning remains. See `frontend-round-2-green.txt` and `frontend-round-2-typecheck-build.txt`.
