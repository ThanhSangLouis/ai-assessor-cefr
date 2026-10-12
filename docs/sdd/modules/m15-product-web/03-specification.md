# M15 — Specification

**Version:** v0.1 · **STATUS:** DRAFT.

## Design tokens/components

Tokens: color semantic, typography scale, spacing, radius, border, elevation, motion duration/easing, breakpoint và z-index. Components: button/icon button, field/select, tabs, badge/status, card/table, dialog/toast, skeleton/empty/error, pagination/disclosure/audio/recorder. Mỗi component có disabled/loading/error/focus-visible API.

## Layout/navigation

- ≥1024: persistent left sidebar; 600–1023 compact rail/drawer; 360–599 top bar + bottom nav.
- Main landmark, skip link, one H1, logical heading, visible focus; icon-only needs accessible name.
- Server supplies role/navigation model; client does not invent entitlement/role.

## Page contracts

Public: `/`, `/login`, `/bands`. Student: `/consent`, `/account`, `/student/upload`, `/progress/{id}`, `/report/{id}`, `/my-responses`, `/my-progress`, `/practice`, lesson/review/result. Teacher: `/review`, detail/stats, `/rate`, sheet, `/teach`, lesson builder, insights. Admin: `/admin` with addressable tab/state plus payment/result/receipt.

Each page declares required API, initial/loading/empty/success/error/conflict/forbidden state, primary action, keyboard order, mobile transformation and forbidden claims. Mutations disable duplicate submit and display request ID without raw exception.

## Assets/motion

All local, hashed/packageable, CSP-compatible. Decorative SVG has `aria-hidden`, `pointer-events:none`, hidden in print and no horizontal overflow. `prefers-reduced-motion` disables page/art/progress animation, never removes information.

## Browser evidence contract

Machine-readable result has revision, route, role, viewport, steps/assertions, console/network/external requests, screenshot path/hash and result. Screenshots supplement assertions, never replace them.
