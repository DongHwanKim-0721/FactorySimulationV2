# Agent Context

Updated: 2026-06-10

Read this first when starting a new session on FactorySimulation.

## Product Direction

FactorySimulation is being upgraded from a single-product, connection-based process-flow simulator into a factory-layout coverage simulator.

The user wants to place the real factory equipment layout in the central diagram, then define each raw material input's route through that equipment. Multiple inputs can share the same equipment, hoists, waiting blocks, and operators, so bottlenecks, waiting time, lead time, and weekly/monthly production estimates are based on shared factory resources rather than isolated product paths.

## Current Source Of Truth

- Current status: `docs/CURRENT_STATE.md`
- Key decisions: `docs/DECISION_LOG.md`
- User-visible change history: `docs/CHANGELOG.md`
- Manual checks: `docs/manual-smoke-checklist.md`
- Current route PRD: `docs/prd/done/route-based-material-routing.md`

Historical PRDs and handoffs are preserved under `docs/prd/archive/` and `docs/handoffs/archive/`. Use them only for background unless `CURRENT_STATE.md` points to them.

## Current Model

- Layout says what equipment exists.
- INPUT blocks say what raw materials enter the factory.
- Each INPUT owns a route of actual non-input block IDs.
- Routes are the active material-flow source of truth.
- Process-flow connections are legacy material-flow data and should not drive route-era simulation.
- Operator assignments are still valid resource constraints and remain separate from material routes.
- Hoists only affect lead time when explicitly included in a route.
- Consecutive repeated route steps collapse into one continuous pass-count operation.

## Important Gotcha

If an INPUT block exists, the app should be treated as route-mode. An empty route should fail with a route validation message, not with an old "missing connection" graph error.

## Code Map

- `app.py`: Tkinter UI, route editor, canvas rendering, result panels, weekly/monthly panel wiring.
- `engine/models.py`: scenario entities, route fields, equipment numbering, operator assignments.
- `engine/simulation.py`: legacy graph simulation and route-based scheduler.
- `engine/scenario_io.py`: save/load, legacy normalization, route/equipment persistence.
- `engine/weekly_production.py` and `engine/monthly_production.py`: production estimate helpers.
- `tests/`: regression coverage for engine, persistence, formatting helpers, animation, and operator library.

## Verification

Run:

```powershell
pytest -q
```

Last known local verification on 2026-06-10:

```text
99 passed
```

Build command used for the desktop executable:

```powershell
pyinstaller --noconsole --onefile --name FactorySimulation main.py
```

The current executable path is `dist/FactorySimulation.exe`.

## Next Best Checks

1. Run the Route-Based Material Simulation section in `docs/manual-smoke-checklist.md`.
2. Confirm GitHub route issues can be closed, but do not close them unless the user asks.
3. If adding new production-planning scope, create a small PRD under `docs/prd/active/` and update `CURRENT_STATE.md`.

