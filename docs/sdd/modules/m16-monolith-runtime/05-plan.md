# M16 — Plan

**Version:** v0.1 · **STATUS:** DRAFT.

## Integration sequence

1. Record G0 baseline, backup/restore and shared contract ownership.
2. Add migration registry and schema groups in order: identity → learning → rating/research → billing → jobs/cleanup.
3. Add repository interfaces/composition providers before domain PRs merge.
4. Harden worker/idempotency/readiness.
5. Integrate route registry and package assets once module APIs freeze.
6. Run targeted integration after each module; then full suite, clean wheel, restore, real-audio smoke and browser matrix on one final state.

## Shared-file policy

Only Thắng edits migration registry, composition root, route registry, manifest, base package config and CI during integration windows. Sang/Nguyên submit interface requirements or bounded patches in owned packages; contract changes merge separately before dependents.

## Required evidence

Baseline/final SHA/fingerprint, migration matrix, backup/restore log, job state test, clean wheel command, full tests/coverage, forbidden scan, real-audio smoke or honest NOT_RUN, browser result, limitations and AI logs.
