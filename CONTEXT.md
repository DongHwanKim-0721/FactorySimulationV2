# FactorySimulation Context

Updated: 2026-07-06

Start new sessions by reading:

- `docs/DOCS_INDEX.md`
- `docs/AGENT_CONTEXT.md`
- `docs/CURRENT_STATE.md`
- `docs/DECISION_LOG.md`

Short version: FactorySimulation V2 has pivoted from a route/canvas Tkinter simulator into a production-planning core. The first planning-core MVP package (#16-#22) is implemented and merged. The existing route/canvas app is frozen as a working prototype, reference implementation, and demo surface. It should not be treated as the future product contract.

The current planning-run workflow can read a real `.xlsx` workbook, run the deterministic planning core, and write a report JSON through a CLI entry point. The next product step is to choose the next output surface: Excel report workbook generation, a sample/template workbook artifact, or UI work.

The new product direction starts from monthly/weekly production plans, historical work-order imports, recipe candidates, equipment master/current snapshots, Excel T.B.D recipes, and user-defined comparison scenarios. Planning must treat Hydraulic (`유압`), STS, and shaped-material (`이형재`) work centers as separate planning domains. AI may propose drafts and recommendations, but deterministic engine logic must verify calculations and scenario comparisons.
