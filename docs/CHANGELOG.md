# Changelog

Updated: 2026-06-10

## 2026-06-10

- Organized documentation into current state, decision log, changelog, PRD status folders, and handoff archive.
- Added `docs/AGENT_CONTEXT.md` as the new-session entry point.
- Route mode is now treated as active when INPUT blocks exist.
- Empty INPUT routes now produce route validation errors instead of legacy missing-connection errors.
- INPUT settings include a route editor with actual equipment selection and `+ pass` / `- pass` controls.
- Route highlight derivation is isolated and covered by helper tests.
- Added regression tests for route-mode empty route handling, route highlights, repeated-pass operator reservation, different machines of the same process type, and legacy route/equipment defaults.
- Rebuilt `dist/FactorySimulation.exe` after route-mode fixes.

## Earlier Milestones

- Added route-based material simulation over actual layout blocks.
- Added route persistence, route review state, and equipment numbering.
- Added operator resource constraints with qualification validation and one-operator-per-block assignment.
- Added visual refresh and process block taxonomy.
- Added weekly/monthly expected production based on realized simulation output.

