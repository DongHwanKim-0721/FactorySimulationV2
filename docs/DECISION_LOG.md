# Decision Log

Updated: 2026-06-11

This log captures decisions that future work should preserve. It is intentionally shorter than a PRD.

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
