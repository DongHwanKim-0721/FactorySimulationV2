# PRD: Operator Resource Constraints

Updated: 2026-06-04

Status: implemented

Implementation note: moved to `docs/prd/done/` on 2026-06-10 during documentation cleanup. Current short status lives in `docs/CURRENT_STATE.md`.

GitHub references:

- PRD issue: #39
- Implementation issue: #40 - Add operator cards with names, qualifications, and scenario persistence
- Implementation issue: #41 - Add validated operator-process assignment links
- Implementation issue: #42 - Gate process starts by assigned operator availability
- Implementation issue: #43 - Make shared-operator scheduling deterministic in complex graphs
- Implementation issue: #44 - Update manual smoke checks for the operator workflow

## Problem Statement

FactorySimulation can already model process blocks, bundle-level quantity flow, hoist transport, bottlenecks, and playback. However, it does not model the human operators who can or cannot perform each process. This means the simulator currently assumes that a process can start as soon as the material flow allows it, even when the real factory would also need a qualified operator to be available.

The user wants to add operators without disturbing existing scenarios. If no operators are placed in a scenario, or if operators are placed but not connected to process blocks, simulation should behave exactly as it does today. Operators should be an optional constraint layered on top of the existing process flow, not a replacement for the current graph model.

The user also needs operator qualification rules. Each operator may be able to perform one or more process types, but one operator can process only one task at a time. If an operator who is qualified for drawing and heat treatment is connected to a bending process, the app should warn the user and reject the connection. Some block types are universal: raw material input, hoist, free block, and work waiting can be handled by any operator regardless of the operator's configured qualifications.

## Solution

Add an optional operator feature to the existing desktop simulator. Operators are created from a separate tab in the left panel, then appear as draggable cards in the central diagram. When the user adds an operator, the app opens an operator settings dialog where they can enter the operator name and select one or more qualified process types.

Operators connect to process blocks using the existing Shift-click connection workflow. Operator-process connections should look visually distinct from normal process-flow connections, but they should be created and deleted with familiar interaction patterns. Operator connection lines should include the same kind of line-level delete control used by process connections.

The simulation engine should remain backward compatible. Without operator assignments, simulation should use the current behavior. With operator assignments, a process connected to an operator may start only when both the process flow is ready and its assigned operator is available. The operator does not change processing time, transport time, capacity, routing, split behavior, join behavior, or hoist behavior. Operator-induced delay is reflected in the existing waiting-time calculations rather than in a new report.

## User Stories

1. As a process simulator user, I want to add operators from a separate tab, so that operators are clearly separate from process blocks.
2. As a process simulator user, I want an operator to appear in the central diagram after I create it, so that I can lay out operators near the processes they support.
3. As a process simulator user, I want to enter an operator name, so that I can recognize real people or roles in the diagram.
4. As a process simulator user, I want to configure multiple possible process types for one operator, so that one operator can be qualified for more than one type of work.
5. As a process simulator user, I want operator qualification to be based on process type, so that one setting applies to all blocks of that type.
6. As a process simulator user, I want raw material input to be universally allowed for operators, so that I do not need to configure a special qualification for material input.
7. As a process simulator user, I want hoist work to be universally allowed for operators, so that transport modeling remains easy to connect.
8. As a process simulator user, I want free blocks to be universally allowed for operators, so that custom process labels do not require separate qualification rules.
9. As a process simulator user, I want work waiting blocks to be universally allowed for operators, so that staging/waiting steps remain simple.
10. As a process simulator user, I want an incompatible operator-process connection to fail with a warning, so that invalid assignments are caught before simulation.
11. As a process simulator user, I want an operator qualified for drawing and heat treatment to be rejected from a bending block, so that the model respects real worker capabilities.
12. As a process simulator user, I want one process block to allow at most one connected operator, so that each process has a clear assigned operator.
13. As a process simulator user, I want a warning when I try to attach a second operator to an already assigned process, so that mistakes are obvious.
14. As a process simulator user, I want one operator to connect to multiple process blocks, so that a flexible operator can support several parts of a line.
15. As a process simulator user, I want one operator to process only one task at a time, so that simulations account for human resource contention.
16. As a process simulator user, I want operators to constrain only start time, so that assigning an operator does not secretly change processing duration.
17. As a process simulator user, I want linear flows such as drawing -> hoist -> postprocess to keep their existing order, so that operators never override material flow.
18. As a process simulator user, I want a downstream process to wait for upstream completion and hoist transport before operator availability matters, so that process logic stays realistic.
19. As a process simulator user, I want multiple ready tasks for the same operator to be handled by the task that became ready first, so that scheduling behavior is understandable.
20. As a process simulator user, I want ties to follow existing process flow order and then block ID, so that equal-time scheduling is deterministic.
21. As a process simulator user, I want an operator to complete the currently waiting bundles for a selected process before moving away, so that operator movement does not feel erratic.
22. As a process simulator user, I want an operator not to wait for future bundles that have not arrived yet, so that the first version does not rely on hidden prediction logic.
23. As a process simulator user, I want an operator to move to another ready process after clearing the current waiting bundles, so that operators do not idle unnecessarily in complex multi-input graphs.
24. As a process simulator user, I want scenarios with no operators to simulate exactly as before, so that existing work and expectations are preserved.
25. As a process simulator user, I want scenarios with unconnected operators to simulate exactly as before, so that visual planning alone does not alter results.
26. As a process simulator user, I want operator-caused delays to appear as normal process waiting time, so that the existing result panel remains simple.
27. As a process simulator user, I want no separate operator report in the first version, so that the app stays focused and the feature remains small.
28. As a process simulator user, I want to delete operator connections using a line delete button, so that removal works like existing connection deletion.
29. As a process simulator user, I want operator connection lines to look different from process-flow lines, so that I can tell resource assignments apart from material flow.
30. As a process simulator user, I want to edit an operator by double-clicking the operator card, so that name and qualifications can be changed after creation.
31. As a process simulator user, I want operator changes to mark existing simulation results stale, so that I know when results need to be rerun.
32. As a process simulator user, I want saved scenarios to include operators, so that my operator layout and assignments are not lost.
33. As a process simulator user, I want saved scenarios to include operator qualifications, so that reloaded scenarios preserve the resource model.
34. As a process simulator user, I want old scenario files without operator fields to load normally, so that backward compatibility is maintained.
35. As a maintainer, I want operators to be represented separately from process blocks, so that resource assignment does not contaminate process-flow graph semantics.
36. As a maintainer, I want operator-process assignments to be represented separately from process connections, so that material routing and resource constraints remain distinguishable.
37. As a maintainer, I want qualification validation to be centralized, so that UI warnings and future import validation use the same rules.
38. As a maintainer, I want the worker-aware scheduler to have a narrow testable interface, so that complex scheduling behavior can be tested without launching the GUI.
39. As a maintainer, I want the existing simulation tests to keep passing unchanged, so that no-operator scenarios are proven stable.
40. As a maintainer, I want scenario persistence tests for operators, so that save/load compatibility does not regress.

## Implementation Decisions

- Operators are a new scenario entity, separate from process blocks.
- Operator-process assignments are a new connection type, separate from process-flow connections.
- Operators have an ID, display name, position, and a set of qualified process type IDs.
- Operator IDs should be managed independently from process block IDs.
- Operator-process assignments should reference one operator and one process block.
- Process-flow connections remain directional. Operator-process assignments are resource links and have no material-flow direction.
- The left panel gains a separate operator tab. The existing process block palette remains intact.
- Clicking the operator add control opens a settings dialog before the operator card is created.
- The operator settings dialog includes a name field and checkboxes for qualified normal process types.
- Operators can be edited after creation through the operator card.
- The connection interaction uses the existing Shift-click pattern.
- The user may start a resource connection from an operator and finish on a process block, or start from a process block and finish on an operator.
- Operator-to-operator connections are invalid.
- Process-block-to-process-block connections continue to create normal process-flow connections.
- Operator-process connections are validated before being added.
- A process block may have at most one assigned operator. A second operator assignment fails with a warning.
- One operator may be assigned to multiple process blocks.
- The universal operator-compatible process types are raw material input, hoist, free block, and work waiting.
- Universal process types do not need to appear as checked qualifications to allow connection.
- Non-universal process types require the operator's qualified process type set to contain the block type.
- Incompatible resource assignments fail at connection time with a warning message and no scenario mutation.
- Deleting a process block also deletes its operator assignments.
- Deleting an operator also deletes its operator assignments.
- Clearing the scenario clears operators and operator assignments as well as process blocks and process-flow connections.
- Scenario save/load includes operators and operator assignments.
- Scenario load treats missing operator fields as an old file and loads successfully with no operators.
- The simulation API should preserve current no-operator behavior. A no-operator or no-assignment scenario should follow the existing simulation path.
- A worker-aware scheduling path should activate only when at least one operator assignment exists.
- Operator availability constrains process start time only.
- Operator assignment does not change operation duration, transport trips, routing weights, split behavior, join behavior, bottleneck throughput formulas, or animation token semantics.
- Existing material-flow readiness remains the first condition. A block cannot start before incoming bundles arrive and upstream flow allows it.
- For an operator assigned to multiple blocks, the next block chosen is the ready work with the earliest ready time.
- If ready times are equal, the deterministic tie-breaker is existing process flow order and then block ID.
- Once an operator begins servicing a process block, that operator should process the bundles already waiting for that block before selecting a different block.
- The first implementation does not predict future arrivals. If the current block's next bundle has not arrived, the operator may move to another block that is already ready.
- Operator-induced delays are included in existing waiting time values.
- The result panel is not expanded with operator utilization, idle time, or resource reports in this version.
- The animation may continue to display existing bundle tokens only. Operator card display and operator connection display are sufficient for the first version.
- Operator changes mark simulation results stale just like process structure changes.
- A small, deep scheduling component should encapsulate operator assignment and availability rules behind a simple simulation-facing interface.
- Qualification validation should be reusable by UI and tests.

## Testing Decisions

- Good tests should verify user-visible behavior and serialized data, not private widget internals or exact canvas coordinates.
- Existing no-operator simulation tests should remain unchanged and passing.
- Engine tests should cover that no operators and no operator assignments preserve existing results.
- Engine tests should cover a worker assigned to two independent process blocks where the second block waits because the worker is busy.
- Engine tests should cover a linear flow where operator assignment does not reorder upstream, hoist, and downstream work.
- Engine tests should cover earliest-ready scheduling for one operator assigned to multiple blocks.
- Engine tests should cover equal-ready tie-breaking by process flow order and block ID.
- Engine tests should cover the "current waiting bundles first, no future prediction" rule in a multi-input or multi-branch scenario.
- Scenario model tests should cover adding, deleting, and cascading operator assignments.
- Scenario persistence tests should cover save/load round trips for operators, operator names, positions, qualifications, and assignments.
- Scenario persistence tests should cover loading old scenario files with no operator fields.
- Validation tests should cover universal block types accepting any operator.
- Validation tests should cover incompatible non-universal process types being rejected.
- Validation tests should cover one process rejecting a second assigned operator.
- UI-level automated tests should stay limited to pure helper behavior where practical, following the existing lightweight app formatting tests.
- Manual smoke testing should verify operator tab creation, operator settings, card dragging, Shift-click assignment, invalid assignment warnings, assignment deletion, save/load, and stale-result behavior.

## Out of Scope

- Frequently used operator templates or a reusable operator library.
- Separate operator utilization, idle time, workload, or efficiency reports.
- Operator Gantt charts or dedicated resource timelines.
- Operator skill levels, speed multipliers, proficiency percentages, or quality effects.
- Shift calendars, breaks, attendance, overtime, or time-window availability.
- Multiple operators assigned to one process block.
- A process requiring multiple operators at the same time.
- Automatic operator assignment or optimization.
- Predictive waiting thresholds such as "stay at this process if the next bundle arrives within N minutes."
- Travel time between process blocks.
- Changing existing process duration math.
- Changing hoist transport semantics.
- Changing split, join, routing, material grouping, or product tracking rules beyond the operator start-time constraint.
- Changing the overall layout into a new screen or workflow.
- Replacing Tkinter or adding a new UI framework.
- Packaging or installer changes.
- Translating the whole app or adding a localization system.

## Further Notes

- The most important product guardrail is backward compatibility: scenarios without operator assignments must behave exactly like today's simulator.
- The second guardrail is conceptual clarity: process-flow connections model material movement, while operator assignments model human resource availability.
- The initial scheduling rule intentionally avoids hidden prediction. The user noted that future bundles can sometimes arrive very soon, but this PRD leaves "same-process hold time" or "operator transfer delay" as a later extension after the baseline feature is working.
- The feature should remain minimal in reporting. Operator constraints can affect total time and existing waiting time, but dedicated operator analytics are intentionally deferred.
