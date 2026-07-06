# Planning Launcher Manual Smoke Checklist

Status: ACTIVE CHECKLIST
Updated: 2026-07-06

Use this checklist before marking a planning launcher PR ready for review. It covers the native Tkinter workbook runner only. It must not expand the frozen route/canvas prototype or add planning calculations in UI code.

## Preconditions

- Current branch is the PR branch.
- `pytest tests/test_planning_launcher.py tests/test_planning_workbook_service.py tests/test_planning_workbook_cli.py tests/test_planning_workbook_io.py -q` passes.
- `pytest -q` passes.
- Worktree changes unrelated to the PR are not staged.

## Standalone Launcher

1. Run `python planning_launcher.py`.
2. Confirm the window title is `Planning Workbook Runner`.
3. Confirm the launcher opens without starting a planning run.
4. Confirm the initial summary asks for a workbook, run metadata, and at least one output path.
5. Close the launcher.

## Desktop App Entry

1. Run the desktop app entry point.
2. Click `Planning workbook` in the toolbar.
3. Confirm a separate `Planning Workbook Runner` top-level window opens.
4. Click `Planning workbook` again.
5. Confirm the existing launcher window is focused instead of creating a duplicate.
6. Close the launcher and confirm the main route/canvas window remains usable.

## Template Actions

1. In the launcher, click `Create sample template` and save to a temporary `.xlsx` path.
2. Confirm a workbook is written.
3. Click `Create blank template` and save to another temporary `.xlsx` path.
4. Confirm a workbook is written.
5. Do not edit the route/canvas prototype while checking template actions.

## Guardrails

1. Leave input workbook and output paths blank.
2. Click `Check run fields`.
3. Confirm the summary lists missing input workbook, missing output path, and missing metadata.
4. Click `Contract`.
5. Confirm the summary points to `docs/planning-workbook-contract.md` and lists required input sheets.
6. Select a non-input report workbook and click `Check workbook`.
7. Confirm missing required workbook sheets are reported without modifying the source workbook.

## Valid Workbook Run

1. Select a valid planning input workbook.
2. Click `Suggest output paths`.
3. Confirm JSON and XLSX report paths use the input workbook stem with `-planning-run-report`.
4. Enter all required run metadata explicitly.
5. Click `Run workbook`.
6. Confirm selected JSON and/or XLSX outputs are written.
7. Confirm the summary shows calculation authority, deferred capabilities, recipe matching counts, skipped scenarios, scenario ranking, and top bottleneck risks.
8. Click `Show outputs` and confirm generated artifact paths are listed.

## Boundary Checks

- The launcher does not implement due-date scheduling.
- The launcher does not implement standard-time calculation.
- The launcher does not treat AI as calculation truth.
- The launcher does not use route/canvas data as the planning source of truth.
- The launcher delegates planning results to the deterministic workbook service.
