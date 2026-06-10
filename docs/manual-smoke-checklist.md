# Manual Smoke Checklist: FactorySimulation

Updated: 2026-06-09

Use this checklist for manual tkinter verification after changes to `app.py`.

## Basic Editing

- Confirm the palette order is: 원자재 투입, 작업대기, 전처리, 구부, 인발, 절단, 열처리, 교정, 후처리, 검사, 포장, 호이스트, Free Block.
- Confirm old visible labels such as 적재, 절단기, 열처리기, 프레스 교정기, and 자동진직도 측정기 do not appear in the palette.
- Add a 원자재 투입 block, edit product name, material name, input quantity, input time, and kg/EA unit weight.
- Confirm normal process and 호이스트 block settings do not show a product-name field.
- Add new normal process blocks and confirm they default to 30 min/EA and 1EA concurrent quantity, except retained 절단 and 열처리 defaults.
- Add a 호이스트 block, edit transport quantity and move time.
- Add, move, connect, delete blocks and connections.
- Confirm connecting into an INPUT block shows a Korean error message.

## Route-Based Material Simulation

- Add multiple non-input equipment blocks and confirm each shows an equipment number.
- Edit equipment numbers and confirm duplicate numbers within the same block type are rejected.
- Confirm the same equipment number is allowed on different block types.
- Add a raw material input block and edit its route using the route editor in the input settings dialog.
- Confirm the route editor lists actual placed non-input blocks and can add/remove/reorder route steps.
- Confirm the `+ pass` and `- pass` controls display consecutive repeated route steps as a pass count such as `x2`.
- Save the input settings and confirm route review is cleared for that input.
- Delete a non-input block used by an input route and confirm the route is cleaned up and review is required.
- Run a simple input route with no process-flow connections and confirm simulation succeeds.
- Confirm an input with a missing/empty route is rejected when route mode is active.
- Confirm selecting an input block highlights only that input route with temporary visual lines.
- Confirm process-to-process material connection creation is hidden in route mode, while operator assignment links still work.
- Confirm consecutive repeated route steps appear as pass counts in route detail.
- Confirm non-consecutive revisits appear as separate route detail steps.
- Confirm an explicit hoist route step affects lead time and an omitted hoist does not.
- Confirm shared equipment creates waiting time when multiple input routes use the same block.
- Confirm result panels and playback time use hours, not minutes.

## Operator Resources

- Open the operator tab and add an operator from the separate operator control.
- Enter an operator name and select qualified process types.
- Double-click the operator card, edit the name and qualified process types, and save.
- Drag the operator card in the central diagram.
- Shift-click an operator, then a process block, and confirm an operator-process assignment line appears.
- Shift-click a process block, then an operator, and confirm the same assignment type is created.
- Delete an operator assignment using the resource line delete control.
- Assign an operator to raw material input, hoist, Free Block, and work waiting blocks without requiring matching qualifications.
- Try assigning an unqualified operator to a non-universal process block and confirm a warning appears with no assignment added.
- Try assigning a second operator to a process block that already has one operator and confirm a warning appears with no assignment added.
- Assign one operator to multiple process blocks and confirm all resource lines remain visible.
- Save and reload a scenario with operators, qualifications, card positions, and assignments.
- Run a simulation, then edit an operator or assignment and confirm the result is marked stale.
- Confirm a scenario with operators but no assignments simulates like the same scenario without operators.
- Confirm a simple shared-operator scenario delays the second ready process through existing waiting time values.
- Confirm the result panel does not add operator utilization, idle-time, or separate operator reports.

## Visual Refresh

- Confirm the main shell keeps the same three-pane layout and window sizing while using the calmer dashboard styling.
- Confirm palette buttons use the approved Korean labels and emojis with consistent spacing and readable text.
- Confirm the canvas background, grid, block outlines, connection lines, delete badges, waiting highlights, processing highlights, and bottleneck badges are easy to read.
- Confirm the right result panel is easier to scan and still keeps the same summary, timeline, analysis, current-time, and selected-bundle content.
- Confirm block setting dialogs have only minor spacing/readability cleanup and the same fields, validation, save, cancel, and Free Block naming behavior.

## Simulation Scenarios

- INPUT-only: total input quantity and final output quantity match the INPUT quantity.
- Multiple INPUT blocks may reuse the same product name and the same product/material pair.
- Serial: INPUT 10EA, input time 0, process 1 min/EA and 1EA capacity, second process 1 min/EA and 1EA capacity produces 20 min total time.
- Input time: same serial scenario with input time 5 min produces 25 min total time.
- Hoist: 10EA with 4EA per move and 3 min per move reports 9 min and 3 moves.
- Branch: downstream weights 4 and 1 split 10EA into 8EA and 2EA without duplicating quantity.
- Join: multiple INPUT lines entering one process keep bundle-level FIFO and do not merge bundles.
- Material grouping: A, B, later A entering a process is handled A, A, B.
- Hoist FIFO exception: the same A, B, later A sequence through HOIST is handled by arrival FIFO.

## Results

- Summary shows total input quantity, final output quantity, total time, unique product-label count, product-label input EA, and product-label output EA.
- Block results show processed EA quantity, processed bundle count, unique product-label count, and unique material count.
- HOIST results show move count.
- Detailed analysis shows product name, material name, bundle quantity, start time, and completion time.
- Branch/join bundle details keep product and material labels without merging same-label bundles.
- Branch/join flow is shown from actual connections, not as a fake linear chain.

## Weekly Expected Production

- Before running simulation, confirm the weekly expected production panel asks the user to run simulation first when a raw material input block exists.
- Confirm a scenario with no raw material input block shows that kg/EA ton conversion is unavailable.
- Edit a raw material input block and confirm kg/EA unit weight must be greater than 0.
- Run a simple INPUT -> process scenario with 10EA and 100 kg/EA.
- Confirm the panel has work-day, daily-hour, and operating-rate controls.
- Confirm daily hours cannot exceed 24 and weekly work days cannot exceed 7.
- Confirm the panel shows expected weekly tons, expected output EA, selected final output EA, weekly operating minutes, and realized minutes/EA.
- Confirm the panel shows 1 ton for 10EA at 100 kg/EA when weekly operating time is long enough.
- Increase work days and daily hours and confirm the panel still does not exceed 1 ton for 10EA at 100 kg/EA.
- Reduce weekly operating time below the simulation elapsed time and confirm expected weekly tons decreases.
- Confirm the panel does not show target tons, feasible/infeasible status, surplus/shortage, weekly CAPA, or bottleneck throughput.
- Create a multi-material input scenario and confirm the input selector starts with an all-raw-materials row, followed by one row per material name, with product/material names visible in each row.
- Confirm the all-raw-materials row uses the total source output EA and output-weighted kg/EA value.
- Change the selected material and confirm the weekly expected production answer updates using that material's combined source output EA and kg/EA value.
- Confirm realized minutes/EA is weekly operating minutes divided by total final output EA, even when the selected material uses only part of the output.
- Modify the scenario after simulation and confirm the weekly expected production panel marks the result stale and avoids presenting it as current.
- Run an instant input-only scenario with zero elapsed time and confirm the panel still converts final output EA to tons.

## Animation

- Run a simulation and confirm the central diagram shows playback controls above the canvas.
- Click play, pause, stop, and confirm stop returns the playhead to 0.0 minutes.
- Change speed between 0.5x, 1x, 2x, and 5x and confirm playhead movement changes.
- Drag the time slider and confirm playback pauses and the diagram updates to the selected time.
- Confirm bundle tokens show product/material labels and EA quantity.
- Confirm waiting bundles stack outside the block and processing bundles appear beside the block without covering block text.
- Confirm a block with waiting bundles gets a subtle warning outline.
- Confirm the bottleneck block shows a small badge and is further emphasized when processing.
- Click a bundle token and confirm the right panel shows selected bundle details.
- Click empty canvas space or press Escape and confirm bundle selection clears.
- Use a large multi-input scenario and confirm compact token mode appears instead of overcrowding the canvas.
- Move a block after simulation and confirm the result remains available, but playback stops.
- Add/delete blocks, add/delete connections, edit parameters, load, or clear and confirm the result is marked as needing rerun.
- Save a scenario and confirm playback/result state does not change.

## Persistence

- Save a scenario containing INPUT product/material labels, process, and HOIST blocks.
- Load the saved scenario and confirm all new fields, including kg/EA unit weight, are preserved.
- Load an older scenario JSON with no `product_name` and confirm INPUT uses default product name `제품`.
- Load an older scenario JSON with no `unit_weight_kg_per_ea` and confirm INPUT uses default unit weight `1 kg/EA`.
- Load an older scenario JSON using `STORAGE`, `STRAIGHTNESS`, and `PRESS`; confirm they become `WORK_WAITING`, `INSPECTION`, and `CORRECTION`.
- Save that normalized legacy scenario again and confirm the JSON contains only the new type IDs.
- Run simulation after load and compare the result with the pre-save run.
