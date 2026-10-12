# M15 — Plan

**Version:** v0.1 · **STATUS:** DRAFT.

## Build slices

1. Inventory routes/API/state and freeze design tokens/component conventions.
2. Implement base shell/nav/assets/components and packaging tests.
3. Public + student assessment/account slice.
4. Learning/progress slice.
5. Teacher review/blind/authoring slice.
6. Admin operations/research/billing slice.
7. Responsive/accessibility/motion polish and full browser matrix.

Nguyên owns templates/static/browser tests; Thắng reviews authorization/API/secret state; Sang reviews AI/statistical wording. Base template/global CSS/route registry are locked shared files: one PR/owner at a time. No inline domain rule or authorization in JS; view models arrive normalized from service/API.

Packaging expands setuptools data for templates, CSS, SVG, WOFF2 and license. Browser evidence belongs to final integrated revision, not mocked standalone pages only.
