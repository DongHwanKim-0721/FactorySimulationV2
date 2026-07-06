# Visual QA

Surface: native Tkinter planning workbook launcher in `planning_launcher.py`.

Status: partial pass for desktop UI. Browser viewport checks at 390, 768, and 1280 px are not applicable because this slice is not a web surface and does not expose an HTML/browser target.

## Checks Run

- `pytest tests/test_planning_launcher.py tests/test_planning_workbook_service.py tests/test_planning_workbook_cli.py tests/test_planning_workbook_io.py -q`
- `pytest -q`

## Results

- Focused planning launcher and workbook tests: 11 passed.
- Full regression suite: 146 passed.
- Route/canvas prototype files were not edited.
- `DESIGN.md` now defines the token contract.
- New launcher code adds no fixed color values.
- Visible strings in the new launcher use zero em-dashes.
- Motion is not claimed or implemented.

## Manual Review Notes

- Initial state: summary tells the user to select a workbook, enter metadata, and choose at least one output path.
- Template actions: sample and blank template buttons call the same service layer as the deterministic workflow.
- Run action: service request maps explicit metadata fields to `PlanningWorkbookRunConfig`.
- Success state: generated paths and compact deterministic summary are formatted from `PlanningWorkbookRunSummary`.
- Error state: workbook validation and request errors are shown without adding calculation logic to UI code.

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
