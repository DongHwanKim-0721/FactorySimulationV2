# Current State

Updated: 2026-07-06

## Product Status

FactorySimulation V2 has pivoted product direction. The implemented Tkinter route/canvas simulator is frozen as a working prototype, reference implementation, and demo. The first production-planning core MVP package (#16-#22) is implemented and merged.

## Current Product Direction

The product now starts from production planning data instead of manual canvas routes:

- Monthly/weekly production plans are the primary planning input.
- Historical work-order routing files are bulk-imported to build recipe candidates.
- Equipment status sheets become equipment master/current snapshots.
- Items or processes missing from the recipe DB are added through controlled Excel T.B.D recipe tables.
- Hydraulic (`유압`), STS, and shaped-material (`이형재`) work centers are separate planning domains.
- Due dates and standard times are later phases.
- Initial priority uses a shortest lead-time proxy.
- Users can define comparison scenarios directly.
- AI can recommend or draft, but deterministic engine logic must verify calculations.

## Current Implemented Planning Core

The planning core currently includes:

- normalized records and fixture harness for planning domains, plan lines, work orders, equipment snapshots, recipes, recipe steps, and scenario definitions
- monthly/weekly production-plan row import and validation
- historical work-order import and recipe candidate extraction
- equipment snapshot import with availability normalization
- same-domain recipe matching, missing recipe/T.B.D reporting, ambiguous recipe reporting, and deprecated recipe exclusion
- load summary and bottleneck-risk proxy reports without standard-time claims
- user-authored scenario workbook normalization, built-in templates, AI-draft gating, and deterministic scenario comparison
- deterministic end-to-end planning-run fixture reporting that chains raw fixture rows through import, matching, load/risk reporting, and scenario comparison
- real `.xlsx` workbook row extraction for the same planning-run report shape
- CLI execution for `workbook.xlsx -> planning-run-report.json`

The next product question is which output surface should come after workbook-to-JSON execution: an Excel report workbook, a sample/template workbook artifact, or a planning-core UI.

## Current Implemented Prototype

The existing application still behaves as a route-based layout simulator:

- Route-based material flow is active when INPUT blocks exist.
- Each INPUT block owns an ordered route of actual non-input block IDs.
- INPUT routes can be edited through canvas click selection.
- Empty routes are invalid in route mode.
- Consecutive repeated route steps are shown and simulated as pass counts.
- Non-consecutive revisits re-enter the same equipment queue.
- Shared equipment creates waiting time across multiple input routes.
- Hoists affect lead time only when explicitly included in a route.
- Operator assignments constrain route step start times without changing duration or capacity.
- Weekly/monthly expected production panels use realized simulation output from the prototype.

Treat this behavior as REFERENCE unless the user explicitly asks for prototype maintenance.

## Active PRDs

- `docs/prd/active/production-planning-pivot.md`: active product/data contract for the production-planning pivot.
- `docs/prd/active/production-planning-mvp-slices.md`: completed implementation sequence for the first production-planning MVP.
- `docs/prd/active/production-planning-issue-drafts.md`: published and completed GitHub issue record for production-planning MVP issues #16-#22.
- `docs/planning-workbook-contract.md`: executable workbook sheet and CLI contract.

GitHub issues #11-#15 have been implemented locally for the route/canvas prototype but should not be closed automatically unless the user asks.

## Reference PRDs

These describe implemented prototype behavior and remain useful for demos, regression checks, and possible future reuse:

- `docs/prd/done/canvas-click-route-selection.md`
- `docs/prd/done/route-based-material-routing.md`
- `docs/prd/done/operator-resource-constraints.md`
- `docs/prd/done/monthly-expected-production.md`
- `docs/prd/done/ui-and-process-block-taxonomy.md`

## Historical Reference

Older phase PRDs and handoffs are preserved for archaeology:

- `docs/prd/archive/`
- `docs/handoffs/archive/`

They should not override `docs/DOCS_INDEX.md`, this file, or the active production-planning PRD.

## Current Verification

Last local automated verification for the combined frozen prototype and planning core:

```text
pytest -q
137 passed
```

The desktop executable was rebuilt with:

```powershell
pyinstaller --noconsole --onefile --name FactorySimulation main.py
```

## Watch-Outs

- Do not continue manual route-editor feature work as the main product path.
- Do not treat canvas routes as the future monthly/weekly planning input.
- Do not merge Hydraulic (`유압`), STS, and shaped-material (`이형재`) planning into one universal equipment pool.
- Do not assume due dates or standard process times exist in the first planning core.
- Do not let AI-generated recommendations replace deterministic validation.
- Do not treat historical handoffs as the current contract.
- Do not close GitHub issues automatically; the user asked to review first.
