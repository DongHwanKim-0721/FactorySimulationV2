# PRD: Route-Based Material Simulation

Updated: 2026-06-09

Status: implemented

Implementation note: moved to `docs/prd/done/` on 2026-06-10 during documentation cleanup. Current short status lives in `docs/CURRENT_STATE.md`.

## Problem Statement

FactorySimulation currently treats material flow as a graph of connected process blocks. That model breaks down for the user's real factory because not every raw material follows the same process sequence. Some materials skip processes, some use different machines of the same process type, and some need repeated passes through the same actual machine.

The most important failing case is continuous drawing. A material can pass through the same drawing machine more than once. A connection-based DAG cannot express that cleanly because it assumes process blocks are connected in a non-cyclic flow and each block appears once in topological order. Forcing repeated machine visits into process-block connections would make the model confusing and error-prone.

The user wants to place the full factory layout first, then define which actual blocks each raw material will pass through at the input stage. Lead time should be calculated from each raw material's route, while sharing the same real equipment, hoists, waiting blocks, and operator constraints.

## Solution

Replace connection-based simulation with route-based simulation.

The factory layout becomes a set of actual placed blocks: process equipment, hoists, work waiting blocks, free blocks, and raw material inputs. Process-to-process connections are no longer the simulation source of truth. Instead, each raw material input block owns a route sequence containing the actual non-input block IDs that material will visit.

Users edit the route from the input block settings dialog. The route is a linear sequence for the first version, but it may include the same block ID multiple times. Consecutive repeated block IDs represent continuous passes through the same machine and are processed as one continuous operation with pass count multiplied into the operation duration. Non-consecutive revisits are treated as separate visits to the same equipment resource and must wait for that equipment and its assigned operator to become available again.

Hoist movement is not automatically inferred. If a hoist should affect lead time, the user must explicitly include the hoist block in the route. Blocks not included in any route still appear in the main result timeline with zero processed quantity, making unused equipment visible.

All time entry and display should use hours. The internal engine may keep its existing numeric fields, but user-facing labels, dialogs, summaries, route details, and result panels should read as hours.

## User Stories

1. As a factory simulation user, I want to place all equipment in the layout before defining raw material flow, so that the layout represents the real factory.
2. As a factory simulation user, I want each raw material input to have its own route, so that different materials do not need to share one process sequence.
3. As a factory simulation user, I want route steps to reference actual placed blocks, so that lead time uses the correct machine capacity and processing time.
4. As a factory simulation user, I want multiple machines of the same process type to be distinguishable, so that I can route material to the correct drawing machine, heat treatment machine, or inspection station.
5. As a factory simulation user, I want equipment to display as process name plus number, so that names like `인발 #3` and `인발 #7` are clear.
6. As a factory simulation user, I want equipment numbers to be assigned automatically, so that creating several machines is fast.
7. As a factory simulation user, I want to manually edit equipment numbers, so that the app can match real factory numbering.
8. As a factory simulation user, I want duplicate equipment numbers within the same block type to be rejected, so that each displayed equipment name points to one real block.
9. As a factory simulation user, I want different block types to be allowed to use the same number, so that `인발 #1` and `열처리 #1` can both exist.
10. As a factory simulation user, I want raw material input blocks to stay identified by product and material name, so that inputs are not confused with equipment.
11. As a factory simulation user, I want all route-capable non-input blocks to have numbers, so that work waiting, hoist, free block, and normal process blocks are all selectable unambiguously.
12. As a factory simulation user, I want custom names to remain available as secondary labels, so that I can add notes like a line name without replacing the stable equipment identifier.
13. As a factory simulation user, I want the input block settings dialog to include route editing, so that route setup happens where raw material setup already happens.
14. As a factory simulation user, I want the route editor to list actual placed blocks, so that I choose real layout objects rather than abstract process types.
15. As a factory simulation user, I want the route editor to allow the same block more than once, so that continuous drawing and repeat processing can be modeled.
16. As a factory simulation user, I want consecutive repeated blocks to display as `xN`, so that repeated passes are easy to read.
17. As a factory simulation user, I want `+ pass` and `- pass` controls, so that I can adjust repeated pass count without duplicating rows manually.
18. As a factory simulation user, I want a single repeated-pass operation to multiply processing time by pass count, so that route duration matches repeated work.
19. As a factory simulation user, I want continuous repeated passes to reserve the same equipment for the whole repeated operation, so that another material cannot interrupt the middle of a continuous pass sequence.
20. As a factory simulation user, I want continuous repeated passes to reserve the assigned operator for the whole repeated operation, so that operator constraints match equipment usage.
21. As a factory simulation user, I want non-consecutive revisits to the same equipment to wait again, so that returning after heat treatment or another process uses the real shared machine queue.
22. As a factory simulation user, I want to route a later revisit to a different machine when needed, so that I can choose `인발 #3` first and `인발 #7` later.
23. As a factory simulation user, I want hoists to affect lead time only when I explicitly include them in the route, so that movement assumptions do not create false bottlenecks.
24. As a factory simulation user, I want route steps such as work waiting or free block to be calculated if included, so that anything in the route has a real time meaning.
25. As a factory simulation user, I want zero-hour non-input route steps to be rejected in the first version, so that route semantics stay clear.
26. As a factory simulation user, I want input time to be included in raw material lead time, so that preparation or loading time affects first process arrival.
27. As a factory simulation user, I want all time inputs to be entered in hours, so that the app matches production planning language.
28. As a factory simulation user, I want all lead time and waiting time results to display in hours, so that I do not need to convert minutes manually.
29. As a factory simulation user, I want total lead time to be the maximum final completion time across all input routes, so that the scenario finish time is clear.
30. As a factory simulation user, I want raw-material-specific lead times, so that I can compare which material route finishes earlier or later.
31. As a factory simulation user, I want equipment shared by multiple raw materials to have one queue, so that lead time reflects real resource contention.
32. As a factory simulation user, I want normal process equipment to use arrival-time FIFO with same-material grouping, so that existing material grouping behavior is preserved.
33. As a factory simulation user, I want hoist blocks to remain FIFO, so that hoist behavior stays simple and predictable.
34. As a factory simulation user, I want assigned operators to constrain route-based simulation, so that human resource limits remain part of lead time.
35. As a factory simulation user, I want a route to fail validation if it is empty, so that missing route setup cannot produce misleading results.
36. As a factory simulation user, I want deleting a block to remove that block from all routes, so that routes never reference missing layout objects.
37. As a factory simulation user, I want inputs affected by block deletion to be marked route review required, so that I know which routes need confirmation.
38. As a factory simulation user, I want saving the input settings route to clear the review-required state, so that the app knows I checked the route.
39. As a factory simulation user, I want simulation to be blocked when an input route is empty or needs review, so that stale or broken route definitions cannot run.
40. As a factory simulation user, I want selecting an input block to show only that material's route as a temporary highlight, so that I can inspect one material flow without clutter.
41. As a factory simulation user, I want route highlight lines to be visual only, so that they do not behave like saved process connections.
42. As a factory simulation user, I want connection creation and editing hidden in the first route-based version, so that I am not confused about whether connections affect simulation.
43. As a factory simulation user, I want unused layout blocks to appear in the result timeline with zero processed quantity, so that I can see equipment that was not used by the scenario.
44. As a factory simulation user, I want the main result to aggregate by actual equipment block, so that bottleneck and throughput are equipment-level.
45. As a factory simulation user, I want route detail to show raw material step history, so that I can understand each material's exact path.
46. As a factory simulation user, I want route detail to show arrival time, start time, completion time, and waiting time, so that I can tell whether delay came from waiting or processing.
47. As a factory simulation user, I want repeated consecutive passes to appear as a pass count in route detail, so that continuous drawing is readable.
48. As a factory simulation user, I want non-consecutive revisits to appear as separate route steps, so that returning to a machine after another process is explicit.
49. As a factory simulation user, I want first-version automatic commentary to be minimal, so that I can trust the numbers before trusting interpretations.
50. As a maintainer, I want route simulation to be isolated behind a testable engine interface, so that scheduling behavior can be verified without the GUI.
51. As a maintainer, I want route fields saved with input blocks, so that scenario persistence matches the new source of truth.
52. As a maintainer, I want connection data to be removed from or ignored by the simulation path, so that there is only one routing model.
53. As a maintainer, I want block numbering validation centralized, so that UI, save/load, and tests use the same uniqueness rules.
54. As a maintainer, I want route cleanup after block deletion to be deterministic, so that broken references do not survive.
55. As a maintainer, I want route-based tests for shared equipment, repeated passes, revisits, hoists, and operators, so that the new core model is protected.

## Implementation Decisions

- Route-based simulation replaces connection-based simulation as the source of truth.
- Process-to-process connections are not required for simulation.
- Connection creation and editing should be hidden or removed in the first route-based version.
- Route highlight lines are derived from selected input route data and are not saved process connections.
- Each input block owns its route.
- Routes contain only non-input block IDs.
- Input block IDs are not stored inside their own route.
- Routes are linear in the first version.
- The same block ID may appear multiple times in a route.
- Consecutive occurrences of the same block ID are collapsed into one service operation with `pass_count`.
- Consecutive repeated passes multiply operation duration by pass count.
- Consecutive repeated passes occupy the equipment resource continuously for the full multiplied duration.
- Consecutive repeated passes occupy the assigned operator continuously for the full multiplied duration.
- Non-consecutive occurrences of the same block ID are separate visits and re-enter that equipment's queue.
- Hoists are not automatically inserted between process steps.
- A hoist contributes transport time and capacity only when explicitly included in the route.
- Work waiting blocks and free blocks are valid route steps and are calculated when included.
- Non-input route steps must have positive processing or transport time in the first version.
- Input time may be zero and is included in raw material lead time.
- The first route step's arrival time is the input block's input time.
- Total scenario lead time is the maximum final completion time across all input routes.
- The first version keeps one bundle per input block.
- Transfer lot or batch splitting is out of scope for the first route-based version.
- Multiple input routes sharing one equipment block share that equipment's availability.
- Normal process blocks use arrival-time FIFO with same-material grouping preserved from the current engine behavior.
- Hoist blocks use FIFO without same-material grouping.
- Operator constraints remain active in the route-based engine.
- Assigned operators constrain start time and availability.
- Operator assignments do not change processing duration, transport duration, capacity, or route order.
- Main results are aggregated by actual block.
- Route details are recorded by input route step.
- Route detail records include input identity, step order, block identity, pass count, arrival time, start time, completion time, waiting time, quantity, and assigned operator when present.
- Route detail should display consecutive repeated blocks as `xN pass`.
- Route detail should display non-consecutive revisits as separate steps.
- Blocks not used by any route remain in the main result timeline with zero processed quantity.
- Bottleneck analysis in the first version uses only used non-input blocks with processed quantity greater than zero.
- Bottleneck selection remains based on the lowest effective throughput.
- Effective throughput formulas remain:
  - Normal process: concurrent capacity divided by processing time.
  - Hoist: transport capacity divided by transport time.
- Waiting time and route detail expose delays caused by shared equipment and operators.
- Automatic explanatory commentary should be minimized in the first version.
- All user-facing time entry and display should use hours.
- Existing field names may remain if changing them would create unnecessary churn, but labels and values presented to users must be hours.
- The implementation should avoid mixing minute and hour semantics in the UI.
- Input block route validation blocks simulation when the route is empty.
- Input block route validation blocks simulation when route review is required.
- Deleting a non-input block removes all occurrences of that block ID from every input route.
- If a route changes due to block deletion, the owning input block is marked route review required.
- Saving the input settings dialog clears route review required for that input.
- The route editor lives in the input block settings dialog for the first version.
- Canvas click route editing is deferred.
- The route editor lists actual placed route-capable blocks.
- The route editor allows repeated pass adjustment with `+ pass` and `- pass`.
- The route editor displays consecutive repeated blocks as `xN`.
- Equipment numbering is stored in a separate numeric field, not parsed from display text.
- Equipment numbering applies to route-capable non-input blocks.
- Input blocks do not get equipment numbers.
- Equipment numbers are scoped by block type.
- A duplicate equipment number within the same block type is invalid and blocks saving.
- The same equipment number may be reused by different block types.
- Equipment numbers are auto-assigned on block creation.
- Users may edit equipment numbers manually.
- Primary block display is process name plus number, such as `인발 #3`.
- Custom names are secondary display text, such as `인발 #3 - 소형 라인`.
- The route editor and result detail should use the primary equipment display and include custom name only as supporting text.
- Scenario persistence stores route block IDs, route review state, and equipment number.
- Scenario persistence no longer needs to preserve connection-based simulation semantics.
- Existing connection-based scenario migration is not required because the user has no saved connection scenarios to preserve.
- The implementation should favor a deep route scheduler module with a narrow interface over scattering route timing across UI code.

## Testing Decisions

- Good tests should verify external behavior: route validation, lead times, shared resource waiting, repeated pass timing, route detail records, saved data, and displayed formatting helpers. Tests should avoid private implementation details unless the helper is intentionally isolated.
- Engine tests should cover a single input with a simple linear route.
- Engine tests should cover an empty input route being rejected.
- Engine tests should cover input time contributing to first step arrival and total lead time.
- Engine tests should cover consecutive repeated visits to the same block being collapsed into one pass-count operation.
- Engine tests should cover consecutive repeated passes multiplying processing duration.
- Engine tests should cover non-consecutive revisits to the same equipment re-entering the equipment queue.
- Engine tests should cover routing to a different machine of the same process type.
- Engine tests should cover multiple inputs sharing one equipment block and being scheduled by arrival time.
- Engine tests should cover same-material grouping for normal process blocks.
- Engine tests should cover hoist FIFO behavior in route mode.
- Engine tests should cover explicit hoist route steps affecting total lead time.
- Engine tests should cover that absent hoist route steps do not add movement time.
- Engine tests should cover unused layout blocks appearing in the timeline with zero processed quantity.
- Engine tests should cover bottleneck selection excluding unused zero-processed blocks.
- Engine tests should cover total lead time as the maximum final route completion across inputs.
- Engine tests should cover route detail records with arrival, start, completion, waiting time, pass count, and quantity.
- Operator-aware engine tests should cover one operator assigned to multiple route blocks.
- Operator-aware engine tests should cover continuous repeated passes holding the operator for the full pass duration.
- Operator-aware engine tests should cover operator waiting appearing as route step waiting time.
- Scenario model tests should cover auto equipment number assignment by type.
- Scenario model tests should cover duplicate equipment number rejection within the same block type.
- Scenario model tests should cover the same equipment number being valid across different block types.
- Scenario model tests should cover block deletion removing all route occurrences and marking affected inputs route review required.
- Scenario persistence tests should cover route block IDs, review state, and equipment number round trips.
- UI helper tests should cover hour formatting and conversion behavior where practical.
- App-level tests should cover route highlight data derivation if it can be isolated from exact canvas coordinates.
- Manual smoke testing should verify input route editing, pass controls, duplicate number validation, route review warnings, route highlighting, hidden connection UI, and result panels in hours.
- Existing simulation and operator tests should be updated or replaced where they assume connection-based routing.

## Out of Scope

- Branching routes for one input.
- Quantity splitting across route branches.
- Automatic hoist insertion.
- Automatic choice of alternate equipment.
- Optimization of route, machine assignment, or operator assignment.
- Transfer lot size, batch size, or partial flow between processes.
- Per-pass custom processing times on the same equipment.
- Per-material or per-product processing time overrides.
- Yield, scrap, defects, rework loops, or quality losses.
- Shift calendars, breaks, overtime, or non-working windows.
- Operator utilization reports, idle reports, or Gantt charts.
- Advanced bottleneck commentary or automatic root-cause explanations.
- Canvas click route editing.
- Support for saved legacy connection-based scenarios.
- Keeping process connections as a parallel simulation model.
- Adding zero-time pass-through route nodes.
- Replacing Tkinter or redesigning the entire application shell.

## Further Notes

- The key product decision is that layout and route are separate concepts. Layout says what exists in the factory. Route says where one input material goes.
- The first implementation should prioritize the engine and route result correctness before detailed UI polish.
- The route scheduler is the highest-risk part and should be treated as a deep, testable module.
- The UI should make it obvious that route highlight lines are temporary visualization, not editable material-flow connections.
- Because all user-facing time moves to hours, labels, result text, and manual checks should be reviewed carefully for leftover minute wording.
