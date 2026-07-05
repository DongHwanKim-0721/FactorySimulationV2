# FactorySimulation Context

Updated: 2026-07-06

Start new sessions by reading:

- `docs/DOCS_INDEX.md`
- `docs/AGENT_CONTEXT.md`
- `docs/CURRENT_STATE.md`
- `docs/DECISION_LOG.md`

Short version: FactorySimulation V2 has pivoted from a route/canvas Tkinter simulator into a production-planning core. The first planning-core MVP package (#16-#22) is implemented and merged. The existing route/canvas app is frozen as a working prototype, reference implementation, and demo surface. It should not be treated as the future product contract.

The next product step is to turn the implemented core into a visible planning run workflow: deterministic end-to-end fixture reports first, then real Excel workbook IO, CLI entry points, or UI work once the report shape is stable.

The new product direction starts from monthly/weekly production plans, historical work-order imports, recipe candidates, equipment master/current snapshots, Excel T.B.D recipes, and user-defined comparison scenarios. Planning must treat Hydraulic (`유압`), STS, and shaped-material (`이형재`) work centers as separate planning domains. AI may propose drafts and recommendations, but deterministic engine logic must verify calculations and scenario comparisons.
