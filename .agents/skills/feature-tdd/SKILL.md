---
name: feature-tdd
description: Implement a bounded feature slice or regression fix with test-first red, green and refactor evidence against an approved feature-workflow specification.
---

# Feature TDD

Read the assigned task's approved spec, plan, state, relevant repository guidance and existing test conventions. Confirm criterion IDs, boundaries, the current cycle/round, and writer ownership with the lead. Do not implement an unapproved design.

For each behavior:
1. Write a meaningful observable test for the approved behavior; run it before production code changes and observe the intended failure. Distinguish a behavioral failure from setup/import/tool errors.
2. Add the smallest coherent implementation that passes it. Run the test and related regressions.
3. Refactor while tests remain green. Apply SOLID to actual responsibilities/dependencies; avoid speculative interfaces and layers.
4. Record test path/name, commands, actual red reason and green/refactor results in the task's `verification.md`, with criterion and revision references. Never reconstruct an unobserved red result after the fact.

Use realistic boundaries and integration tests where unit tests cannot demonstrate the requirement. For each confirmed implementation defect found during implementation, review, or QA, write a specific regression test that reproduces the reported issue and observe it fail before fixing the defect; then run it to demonstrate the fix and record the evidence. This applies in both initial and correction cycles, including late repairs. For a documentation-only or non-executable change, explain why an executable red step does not apply and verify the actual artifact; do not add tests that mirror prose.

Preserve requirements and existing valid tests. Do not delete, skip, loosen or change expected behavior merely to pass. If a test/spec is wrong or architecture is insufficient, present evidence to the lead and wait for the appropriate decision.

Integrate the slice, update affected usage/architecture documentation and durable local instructions where justified, then run planned related checks. Follow the main workflow's snapshot procedure. Under the granted writer token, update only owned implementation/state fields, attach evidence and return ownership. Return changed files, integrated snapshot, results, open problems and next action. The author does not issue independent review or QA approval.
