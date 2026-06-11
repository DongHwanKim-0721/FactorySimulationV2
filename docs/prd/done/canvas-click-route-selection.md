# Canvas Click Route Selection

## Problem Statement

Raw material INPUT routes are currently edited through a combo box and route list inside the INPUT settings dialog. Users already place the real factory equipment layout on the central canvas, but route setup makes them leave that spatial context and find equipment again from a list.

## Solution

Add a canvas route selection mode that starts from the INPUT settings dialog. The user saves the INPUT's product/material/quantity fields, clicks placed non-input equipment in route order, reviews the temporary route through a small panel plus canvas badges/lines, and completes the selection to save `route_block_ids`.

## User Stories

1. As a factory simulation user, I want to define an INPUT route by clicking placed equipment, so that route setup matches the real layout.
2. As a user, I want route selection to start from the INPUT settings dialog, so that product/material setup and route setup stay connected.
3. As a user, I want existing routes to load into the selection panel, so that I can revise instead of rebuilding from scratch.
4. As a user, I want consecutive clicks on the same equipment to become `xN pass`, so that repeated passes are easy to enter.
5. As a user, I want non-consecutive revisits to remain separate steps, so that returning to shared equipment is explicit.
6. As a user, I want route order badges and temporary route lines, so that I can verify the path visually.
7. As a user, I want remove, move up/down, and reset controls, so that I can recover from click mistakes.
8. As a user, I want invalid clicks to show a status message without popups, so that route entry stays fast.
9. As a user, I want route completion to fail when the route is empty, so that invalid route-mode data is not saved.
10. As a maintainer, I want this UX to reuse `route_block_ids`, so that simulation and persistence contracts do not change.

## Implementation Decisions

- Add route selection UI state in the Tkinter app: selected INPUT id, temporary route steps, original route snapshot, and selected route row.
- Add a non-modal route selection panel near the canvas with route list, complete, cancel, reset, remove, up, and down controls.
- In route selection mode, canvas clicks on non-input blocks append to the temporary route; INPUT blocks, operators, tokens, and empty space do not change the route.
- During route selection mode, block dragging and connection creation are disabled.
- Draw temporary route lines and order badges separately from saved process connections and selected-route highlights.
- On completion, expand route steps into `route_block_ids`, set `route_review_required = False`, mark simulation stale, and redraw.
- Keep the existing list-based route editor as a secondary/manual editor in the INPUT settings dialog.
- Do not change the engine model, scenario persistence, or simulation API.

## Testing Decisions

- Add focused helper tests for append, consecutive pass collapse, non-consecutive revisit, reset, remove, reorder, and empty completion rejection.
- Add app-level or helper-level tests for temporary route edge and badge derivation without depending on exact canvas pixels.
- Reuse existing route helper and route highlight tests as prior art.
- Manual smoke test: create equipment layout, edit INPUT, enter click selection mode, click route, verify badges/lines, complete, run simulation, verify route-mode validation still works.

## Out of Scope

- Branching routes or quantity splitting.
- Automatic hoist insertion.
- Automatic equipment optimization or alternate machine selection.
- Per-material processing time overrides.
- Replacing Tkinter or redesigning the whole application shell.
- Reintroducing process-flow connections as material-flow source of truth.

## Further Notes

- Route-capable targets remain all non-input blocks, including hoists, waiting blocks, free blocks, and normal process equipment.
- Hoists remain explicit route steps; they are never inserted automatically.
