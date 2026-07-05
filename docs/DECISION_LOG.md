# Decision Log

Updated: 2026-07-06

This log captures decisions that future work should preserve. It is intentionally shorter than a PRD.

## 2026-07-06: Initial Planning-Core MVP Is Complete

The first production-planning MVP package (#16-#22) is implemented and merged. The completed core covers normalized contracts, production-plan import, historical work-order recipe candidates, equipment snapshots, same-domain recipe matching, T.B.D reporting, load/risk proxy reporting, and user-authored scenario comparison.

Reason: the codebase now has enough deterministic planning-core behavior to stop adding isolated model slices and start stabilizing the visible planning-run workflow.

## 2026-07-06: End-To-End Fixture Reports Are The Next Stabilization Layer

Before adding real Excel workbook IO, CLI commands, or a planning-core UI, the repo should keep a deterministic end-to-end fixture report that proves raw planning rows can flow through import, recipe matching, load/risk reporting, and scenario comparison.

Reason: the report shape is the bridge between engine internals and future user-facing surfaces. Fixing it first reduces churn when Excel and UI entry points arrive.

## 2026-07-06: Workbook-To-JSON CLI Is The First Executable Planning Surface

The first real user-facing run surface reads a `.xlsx` planning workbook, converts each required sheet into the existing row-dict importer inputs, and writes the deterministic planning-run report JSON. Runtime metadata such as plan batch, plan period, equipment snapshot batch, snapshot timestamp, T.B.D import batch, and engine version is supplied by CLI arguments rather than inferred silently from workbook cells.

Reason: this keeps Excel IO thin, preserves deterministic report shape as the product boundary, and avoids adding UI or scheduling assumptions before the planning report contract is stable.

## 2026-07-06: Report Workbooks Are Derived From The JSON Snapshot

The Excel report workbook export is derived from the deterministic planning-run JSON snapshot instead of recalculating planning results separately. Its sheets expose run metadata, recipe matching, T.B.D rows, load summary, bottleneck risk, and scenario comparison.

Reason: JSON remains the audit-stable report contract while the Excel workbook becomes a planner-facing presentation surface. This avoids divergent report calculations.

## 2026-07-01: Route/Canvas Prototype Is Frozen

The implemented Tkinter route/canvas simulator is frozen as a working prototype, reference implementation, and demo. Future product work should not keep extending the manual route editor unless the user explicitly asks for prototype maintenance.

Reason: the real product need has shifted from hand-built equipment routes to production planning from imported plan, recipe, work-order, and equipment data.

## 2026-07-01: Production Planning Core Is The New Product Direction

The next product contract starts from monthly/weekly production plans, recipe DB records, historical work-order routing imports, equipment master/current snapshots, and Excel T.B.D recipe tables. Manual canvas routes are not the future source of truth for monthly planning.

Reason: planning users need load, bottleneck, missing-recipe, and comparison-scenario outputs from operational planning data, not only a spatial route simulation.

## 2026-07-01: Work Centers Are Separate Planning Domains

Hydraulic (`유압`), STS, and shaped-material (`이형재`) work centers must be modeled as separate planning domains. A whole-factory scenario may compare or aggregate them, but recipe lookup, equipment matching, and capacity assumptions should decompose by work center. Cross-work-center substitution is not allowed unless explicitly configured later.

Reason: each work center has distinct recipe/equipment meaning. A shared generic pool would create false feasibility.

## 2026-07-01: Recipe DB Grows From History And T.B.D Recipes

Historical work-order routing imports should produce recipe candidates. Users confirm, revise, deprecate, or add missing recipes through a controlled Excel T.B.D recipe format.

Reason: the first system should bootstrap from real execution history while keeping human control over uncertain or missing product/process knowledge.

## 2026-07-01: Due Dates And Standard Times Are Later Phases

The initial planning core must not pretend that due dates or standard process times are available. It should support later addition of those fields, but early ranking should use a shortest lead-time proxy.

Reason: available data can support relative planning signals earlier than precise schedule commitments.

## 2026-07-01: Users Can Define Comparison Scenarios

Scenario definitions should be explicit user-authored planning inputs. Built-in defaults can include shortest lead-time proxy, heavy-weight-first, customer-priority, equipment-unavailable, and bottleneck-avoidance rules, but the user should be able to write alternatives directly.

Reason: scenario comparison is the planning workflow. AI recommendations are useful only when the user can inspect and change the assumptions.

## 2026-07-01: AI Advises, Deterministic Engine Verifies

AI may draft recipes, scenario rules, summaries, and recommendations. It must not be the authority for calculation correctness. Deterministic engine logic must produce the load summaries, missing-recipe counts, bottleneck risk signals, and scenario comparison outputs.

Reason: planning decisions need repeatable, auditable calculations.

## Frozen Prototype Decisions

The following decisions remain valid for the frozen route/canvas prototype and reference PRDs. They should not be confused with the new production-planning core contract.

## 2026-06-10: Layout And Route Are Separate Concepts

The central diagram represents the real factory layout: equipment, hoists, waiting blocks, free blocks, operators, and raw material inputs. Material flow is not defined by process-to-process connections. Each INPUT block defines its own route through actual placed equipment.

Reason: product families and raw materials do not share one universal process path. Modeling each product separately hides shared equipment queues, bottlenecks, and waiting time.

## 2026-06-10: INPUT Means Route Mode

When an INPUT block exists, the application should behave as route-mode. If the route is empty, simulation should fail with a route validation error. It should not fall back to legacy connection graph validation and complain about missing process-flow connections.

Reason: connection-based material flow is no longer the route-era source of truth.

## 2026-06-10: Hoists Are Explicit Route Steps

Hoist movement is not inferred between process steps. A hoist contributes transport time, capacity, trips, and waiting only when it appears in an INPUT route.

Reason: automatic movement assumptions can create false bottlenecks.

## 2026-06-10: Repeated Consecutive Steps Are Continuous Passes

Consecutive occurrences of the same block in a route collapse into one route step with a pass count. The equipment and assigned operator are reserved continuously for the multiplied duration.

Reason: continuous drawing can pass through the same machine multiple times without releasing the resource between passes.

## 2026-06-10: Non-Consecutive Revisits Re-Queue

If a route returns to the same equipment after another block, that later visit is a separate route step and waits for the equipment and assigned operator again.

Reason: this models returning to a shared real machine after other work has happened.

## 2026-06-10: Production Estimates Use Realized Simulation Output

Weekly/monthly expected production should use the current simulation result and source-block output quantities. It should not become a theoretical CAPA or target-feasibility panel.

Reason: the user wants practical expected output from the modeled scenario, not a bottleneck-only planning calculator.

## 2026-06-11: Canvas Route Selection Is An Editing UI Only

INPUT route selection may be driven by clicking placed non-input blocks on the canvas. The temporary selection lines and order badges are visual editing aids only. Completing the selection saves the route back to the INPUT block's `route_block_ids`; it does not create process-flow connections or introduce a second material-flow model.

Reason: users should define routes in the same spatial layout where equipment is placed, while preserving INPUT-owned routes as the only active route-era material-flow source of truth.
