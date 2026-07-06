# Production Planning UI Slices

Status: ACTIVE / DRAFT
Updated: 2026-07-06
Parent PRD: `docs/prd/active/production-planning-pivot.md`
Depends on: `docs/planning-workbook-contract.md`

## Purpose

This document defines the next small planning-core UI direction after the workbook CLI workflow. The goal is to make the existing deterministic planning run visible without reopening the frozen route/canvas prototype as the planning source of truth.

The current backend contract is:

1. Create or edit a planning input workbook.
2. Run the deterministic planning core with explicit run metadata.
3. Write a JSON snapshot or Excel report workbook.
4. Inspect recipe matching, T.B.D rows, load summary, bottleneck risk, and scenario comparison.

The UI should wrap that workflow. It should not add new planning calculations.

## Product Boundary

The first planning UI is a workbook-runner surface, not a route/canvas editor.

It may:

- create a sample or blank planning workbook template
- choose an input workbook
- collect required run metadata
- run the same deterministic core used by the CLI
- write JSON and Excel report outputs
- show a compact run summary from the deterministic report
- open or reveal generated files

It must not:

- use canvas routes as the planning source of truth
- modify the frozen route/canvas editor behavior
- implement due-date scheduling
- implement standard-time calculation
- let AI become the authority for calculated results
- silently infer missing batch ids, periods, or snapshot timestamps

## User Stories

1. As a planner, I want to create a template workbook from the app, so that I do not have to remember sheet names and headers.
2. As a planner, I want to choose an existing workbook and run it, so that I can produce deterministic reports without using the command line.
3. As a planner, I want to enter run metadata explicitly, so that reports remain reproducible and auditable.
4. As a planner, I want to choose JSON and/or Excel report outputs, so that I can either inspect raw deterministic data or share a workbook with other planners.
5. As a planner, I want to see a compact success/failure summary, so that validation errors and missing-recipe counts are visible immediately.
6. As a developer, I want the UI to call the existing planning-core workflow, so that UI work does not fork calculation behavior.

## UI MVP Slices

### Slice 1: Planning Run Launcher Shell

Create a new planning-run launcher surface that is visually and behaviorally separate from the route/canvas prototype.

Acceptance criteria:

- The route/canvas prototype remains unchanged.
- The launcher has fields for input workbook, output JSON path, output report workbook path, plan batch id, plan period, plan type, work-order import batch id, equipment snapshot batch id, equipment snapshot timestamp, T.B.D import batch id, and engine version.
- The launcher can create a sample template workbook and a blank template workbook by calling the same template writer used by the CLI.
- No planning calculations are implemented in UI code.

### Slice 2: Deterministic Run Execution

Wire the launcher to the existing workbook workflow.

Acceptance criteria:

- Running with a valid workbook writes the selected JSON and/or Excel report outputs.
- Validation errors from the planning workbook are shown without crashing the app.
- A successful run shows the generated output paths and a compact summary.
- The same workbook and metadata produce the same report as the CLI.

### Slice 3: Report Summary View

Show a compact read-only summary of the deterministic report.

Acceptance criteria:

- The summary shows calculation authority and deferred capabilities.
- The summary shows matched, missing, ambiguous, and T.B.D counts.
- The summary shows scenario ranking rows with deterministic scores.
- The summary shows top bottleneck-risk rows and signals.
- AI explanation fields remain blank or clearly separated from deterministic metrics.

### Slice 4: Workbook Contract Guardrails

Add UI guardrails for workbook contracts without replacing Excel as the authoring surface.

Acceptance criteria:

- The UI can tell the user which required workbook sheets are missing.
- The UI can show missing required run metadata before execution.
- The UI links or points to the workbook contract document.
- The UI does not try to auto-repair source workbooks silently.

## Open Design Questions

- Should the planning-run launcher live inside the existing Tkinter desktop app as a separate top-level tab/window, or as a separate entry point?
- Should generated report files be opened automatically, or should the UI only reveal paths?
- Should the report summary read from JSON only, or also from generated Excel report workbooks?
- What naming convention should the UI use for output files when the planner leaves output paths blank?

## Recommended First Implementation

Start with Slice 1 and Slice 2 together as one thin vertical slice:

- no new planning math
- no route/canvas changes
- no standard-time or due-date fields
- call the existing workbook template writer and deterministic workbook runner
- verify by running the same fixture workbook through both CLI and UI-facing service code

This gives planners a visible workflow while preserving the CLI as the stable automation path.
