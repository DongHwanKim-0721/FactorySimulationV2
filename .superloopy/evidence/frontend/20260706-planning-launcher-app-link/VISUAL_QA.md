# Visual QA

Surface: native Tkinter app toolbar link plus planning workbook launcher preflight.

Status: partial pass for desktop UI. Browser viewport checks at 390, 768, and 1280 px are not applicable because this is a native Tkinter desktop surface, not an HTML/browser target.

## Changes Checked

- Existing desktop app toolbar now exposes `Planning workbook`.
- The toolbar action opens a separate `Planning Workbook Runner` top-level window.
- Reopening the action focuses the existing planning window instead of creating duplicates.
- The planning window adds `Check workbook`, which inspects required input workbook sheets without running calculations.
- Missing planning workbook sheets are shown in the summary text without modifying the source workbook.

## Checks Run

- `pytest tests/test_planning_launcher.py tests/test_planning_workbook_service.py tests/test_planning_workbook_cli.py tests/test_planning_workbook_io.py -q`
- `pytest -q`

## Results

- Focused planning launcher and workbook tests: 14 passed.
- Full regression suite: 149 passed.
- Route/canvas calculation and editing paths were not changed.
- `DESIGN.md` remains the token contract.
- New UI strings use zero em-dashes.
- No new color values were added.
- Motion is not claimed or implemented.

## Anti-Slop Pre-Flight

- Zero em-dashes in new visible strings: pass.
- Eyebrow count: pass, no eyebrow labels.
- No AI-purple or glow default: pass.
- Non-default, deliberate font stack: pass, follows existing Tkinter Arial stack.
- No beige/brass palette: pass.
- Color, shape, and theme consistency locks: pass for new code.
- Layout family variety: not applicable, single desktop tool surface.
- No fake screenshots or fake assets: pass.
- Copy self-audit: pass.
- No micro-tells from catalogue: pass.
- Motion claimed equals motion implemented: pass, no motion claimed.
- Token trace: pass for new UI values through `DESIGN.md`.
- Interactive and error states: covered by code paths and tests, visual browser capture not applicable.
- Horizontal scroll at web breakpoints: not applicable for native Tkinter.
