# Visual QA

Surface: native Tkinter planning workbook launcher run preflight and contract reference.

Status: partial pass for desktop UI. Browser viewport checks at 390, 768, and 1280 px are not applicable because this is a native Tkinter desktop surface, not an HTML/browser target.

## Changes Checked

- `Check run fields` reports missing input workbook, missing output path, and missing required run metadata before execution.
- `Run workbook` now stops before calling the deterministic service when run metadata or output paths are missing.
- `Contract` points users to `docs/planning-workbook-contract.md` and lists required input sheets.
- The launcher still delegates all calculations to the deterministic workbook service.

## Checks Run

- `pytest tests/test_planning_launcher.py tests/test_planning_workbook_service.py tests/test_planning_workbook_cli.py tests/test_planning_workbook_io.py -q`
- `pytest -q`

## Results

- Focused planning launcher and workbook tests: 17 passed.
- Full regression suite: 152 passed.
- Route/canvas calculation and editing paths were not changed.
- `DESIGN.md` remains the token contract.
- New visible strings use zero em-dashes.
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
