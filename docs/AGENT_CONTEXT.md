# Agent Context

Updated: 2026-07-06

Read `docs/DOCS_INDEX.md` before this file when starting a new session on FactorySimulation.

## Product Direction

FactorySimulation V2 has pivoted into a production-planning core. The first planning-core MVP package (#16-#22) is implemented and merged. The product should now turn that core into a visible planning run workflow: import planning data, map plan lines to recipes, combine current equipment status, compare scenarios, and emit deterministic reports.

The existing route/canvas Tkinter simulator still works, but it is now a frozen prototype and reference/demo implementation. Do not continue feature development on the manual route editor unless the user explicitly asks for prototype maintenance.

## Current Planning Core Implementation

- #16: normalized planning contracts and fixture harness.
- #17: production-plan import and validation.
- #18: historical work-order import and recipe candidate extraction.
- #19: equipment snapshot import.
- #20: same-domain recipe matching plus missing/T.B.D reporting.
- #21: load summary and bottleneck-risk proxy reporting.
- #22: user-authored scenario normalization and deterministic comparison.

The current next step is to stabilize end-to-end planning-run reports before committing to Excel workbook IO, CLI, or UI surfaces.

## Current Source Of Truth

- Documentation map and trust levels: `docs/DOCS_INDEX.md`
- Current status: `docs/CURRENT_STATE.md`
- Key decisions: `docs/DECISION_LOG.md`
- Active planning PRD: `docs/prd/active/production-planning-pivot.md`
- Route/canvas reference PRDs: `docs/prd/done/route-based-material-routing.md` and `docs/prd/done/canvas-click-route-selection.md`

Historical PRDs and handoffs are preserved under `docs/prd/archive/` and `docs/handoffs/archive/`. Use them only for background unless a current document points to them.

## New Planning Core Contract

- The future source of truth is production-plan lines, recipe DB records, historical work-order routing imports, equipment master/current snapshots, and Excel T.B.D recipe tables.
- Hydraulic (`유압`), STS, and shaped-material (`이형재`) work centers are separate planning domains with their own recipe and equipment pools.
- Cross-work-center substitution is not allowed by default.
- Missing recipes should become explicit T.B.D recipe work, not silent assumptions.
- Due dates and standard process times are later phases.
- Initial priority uses a shortest lead-time proxy, not precise promised lead time.
- Users must be able to write comparison scenarios directly.
- AI may recommend, draft, or explain scenarios and recipes. Deterministic engine logic must verify calculations.

## Frozen Prototype Contract

The route/canvas app remains useful as a demo and implementation reference:

- Layout says what equipment exists.
- INPUT blocks say what raw materials enter the factory.
- Each INPUT owns a route of actual non-input block IDs.
- Routes are the route-era material-flow source of truth.
- INPUT routes can be edited through canvas click selection.
- Process-flow connections are legacy material-flow data and should not drive route-era simulation.
- Operator assignments are separate resource constraints.
- Hoists only affect lead time when explicitly included in a route.
- Consecutive repeated route steps collapse into one continuous pass-count operation.

This prototype contract should not be expanded into the new production-planning product unless a future PRD explicitly reuses part of it.

## Code Map For Reference

- `engine/planning_core/`: production-planning contracts, importers, recipe matching, load/risk reports, scenario comparison, and deterministic report rendering.
- `app.py`: Tkinter UI, route editor, canvas rendering, result panels, weekly/monthly panel wiring.
- `engine/models.py`: scenario entities, route fields, equipment numbering, operator assignments.
- `engine/simulation.py`: legacy graph simulation and route-based scheduler.
- `engine/scenario_io.py`: save/load, legacy normalization, route/equipment persistence.
- `engine/weekly_production.py` and `engine/monthly_production.py`: production estimate helpers.
- `tests/`: regression coverage for engine, persistence, formatting helpers, animation, and operator library.

## Verification For Existing Prototype

Run:

```powershell
pytest -q
```

Last known local verification on 2026-07-06:

```text
134 passed
```

Build command used for the desktop executable:

```powershell
pyinstaller --noconsole --onefile --name FactorySimulation main.py
```

The current executable path is `dist/FactorySimulation.exe`.

## Next Best Checks

1. For product-direction work, read `docs/prd/active/production-planning-pivot.md`.
2. For prototype maintenance only, run the route-based manual checks in `docs/manual-smoke-checklist.md`.
3. Do not close GitHub issues #11-#15 automatically; the user asked to review first.
