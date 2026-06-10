# PRD: Monthly Expected Production

Updated: 2026-06-04

Status: implemented

Implementation note: moved to `docs/prd/done/` on 2026-06-10 during documentation cleanup. Current short status lives in `docs/CURRENT_STATE.md`.

## Problem Statement

FactorySimulation users want a monthly production estimate in tons. The app already simulates process flow, input quantities, routing, hoist movement, operator waiting, and final output quantities in EA. The monthly production feature should use those realized simulation results, not theoretical bottleneck capa.

The user explicitly does not want a monthly CAPA or bottleneck-based feasibility feature. Target tonnage, feasible/infeasible status, surplus, shortage, and bottleneck throughput should not be part of this panel.

## Solution

Replace the monthly capa panel with a monthly expected production panel. After simulation, the user selects a raw material input block and enters monthly operating assumptions: operating days, daily operating hours, and operating rate percentage.

The selected input block provides `kg/EA`. The simulation result provides the final output EA that originated from that input block and the elapsed simulation time. The panel estimates how much of the simulated output can be completed within the monthly operating time, while never exceeding the simulated final output quantity:

```text
available monthly minutes =
  operating days
  * daily operating hours
  * 60
  * operating rate percentage / 100

expected output EA =
  min(
    selected input final output EA,
    selected input final output EA / simulation elapsed minutes * available monthly minutes
  )

monthly expected tons =
  expected output EA
  * unit weight kg per EA
  / 1000
```

This makes the result an expected production estimate based on the current scenario's simulated output quantity and monthly operating time. Work days, daily hours, and operating rate may reduce the estimate when time is insufficient, but they must not inflate output beyond the modeled final output quantity. Bottleneck throughput is not used.

## User Stories

1. As a process simulator user, I want to see expected monthly production in tons, so that I can compare a simulated process with monthly planning units.
2. As a process simulator user, I want the estimate to use actual simulation output quantity, so that the displayed tons match the modeled input/output volume.
3. As a process simulator user, I want to select a raw material input block, so that the correct kg/EA conversion is used.
4. As a process simulator user, I want the selected input to be tracked by source block, so that same product or material labels are not accidentally merged.
5. As a process simulator user, I want to enter work days, daily hours, and operating rate, so that the app can reduce expected production when monthly operating time is insufficient.
6. As a process simulator user, I do not want target tonnage, feasible/infeasible status, surplus, shortage, or bottleneck throughput in this feature.
7. As a maintainer, I want the monthly production calculation isolated behind a small pure helper, so that the math is testable without launching Tkinter.

## Implementation Decisions

- Use the smaller of selected input final output EA and the EA that can be processed during monthly available minutes at the realized simulation output rate.
- Store final output quantities by `source_block_id` in `SimulationResult`.
- Keep kg/EA on raw material input blocks.
- Show monthly operating days, daily operating hours, and operating rate fields in the right-side result panel.
- Do not use `bottleneck_id` or `bottleneck_throughput` for monthly expected production.
- Do not show target monthly tons, feasible/infeasible status, surplus, or shortage.
- If there is no simulation result, ask the user to run simulation first.
- If the result is stale, hide the monthly estimate until simulation is rerun.
- Elapsed simulation time may reduce monthly expected tons when monthly available time is shorter than the simulated elapsed time, but it must not increase tons beyond selected input final output EA.

## Out of Scope

- Monthly CAPA or bottleneck-based capacity feasibility.
- Monthly target feasibility checks.
- Product mix optimization or demand allocation.
- Yield, scrap, defect, rework, inventory, breaks, holidays, overtime, or shift calendars.
- Exported monthly production reports.
