# Production Planning MVP Slices

Status: COMPLETED
Updated: 2026-07-06
Parent PRD: `docs/prd/active/production-planning-pivot.md`

## Purpose

This document turns the production-planning pivot PRD into an implementation sequence. It is not a coding task by itself. The approved slices were published to GitHub as issues #16-#22 on 2026-07-01.

The goal was to keep the first MVP small, deterministic, and reviewable. The package was implemented through GitHub issues #16-#22 and PRs #23-#29.

## Completion Status

Completed on 2026-07-06 after PR #29 was squash-merged.

- #16: completed by PR #23.
- #17: completed by PR #24.
- #18: completed by PR #25.
- #19: completed by PR #26.
- #20: completed by PR #27.
- #21: completed by PR #28.
- #22: completed by PR #29.

This document remains the baseline implementation record for the first planning-core MVP. New product slices should build on this package instead of adding route/canvas planning-source behavior.

## Slice Rules

- Build data/engine contracts before UI.
- Preserve the frozen route/canvas prototype as REFERENCE only.
- Use Excel-first user workflows, but normalize into deterministic internal records.
- Treat Hydraulic (`유압`), STS, and shaped-material (`이형재`) as separate planning domains.
- Do not assume due dates or standard process times.
- Do not let AI-generated drafts become verified planning results without user confirmation and deterministic validation.
- Prefer slices that produce a verifiable report or fixture output, even before a UI exists.

## Slice 1: Normalized Planning Contracts And Fixture Harness

Type: AFK
Blocked by: None

Create the minimal planning-core contract surface and a fixture-driven verification harness. This slice proves that the MVP can represent the future source of truth without touching the route/canvas prototype.

What it should demonstrate:

- normalized records for planning domain, production plan line, work-order operation, equipment snapshot, recipe header, recipe step, and scenario definition
- stable source-row traceability
- UTF-8-safe handling of `유압`, `STS`, and `이형재`
- deterministic fixture loading and report snapshots

User stories covered:

- 3, 12, 19, 20

PRD acceptance criteria covered:

- 13, 15, 18

Exit criteria:

- Same fixture input produces the same normalized objects and report snapshot every run.
- Planning-domain labels preserve Korean source names while exposing normalized domain codes.
- No implementation depends on manual INPUT routes or canvas route data.

## Slice 2: Production Plan Import And Validation

Type: AFK
Blocked by: Slice 1

Import monthly and weekly production-plan rows into `ProductionPlanLine` records. This slice focuses on demand input quality, not recipe matching.

What it should demonstrate:

- import of customer, flexible order reference, order type, product group, item code, item name, quantity, and weight
- header trimming and source-row traceability
- preservation of raw source values
- validation errors for missing required planning fields

User stories covered:

- 1, 2, 3, 4

PRD acceptance criteria covered:

- 1, 2, 3

Exit criteria:

- A monthly plan fixture imports with correct row count and totals.
- Informal customer/order references are accepted as flexible references.
- Headers with leading or trailing whitespace still map correctly.
- Invalid rows are reported without crashing the whole import.

## Slice 3: Historical Work-Order Import And Recipe Candidate Extraction

Type: AFK
Blocked by: Slice 1

Import historical work-order operation rows and extract recipe candidates by planning domain and item. This slice creates candidate process steps from execution history but does not yet decide final plan matching.

What it should demonstrate:

- work-order route reconstruction by domain, item, work order, process sequence, and operation sequence
- candidate recipe grouping with source work-order evidence
- usage count and last-observed metadata
- distinction between historical candidates and user-confirmed recipes

User stories covered:

- 5, 6, 9, 10

PRD acceptance criteria covered:

- 4

Exit criteria:

- Historical WO fixtures produce candidate recipe headers and ordered recipe steps.
- Candidate recipes retain source work-order references.
- Candidates from one planning domain are not grouped with another planning domain.
- Missing standard times do not block candidate extraction.

## Slice 4: Equipment Snapshot Import

Type: AFK
Blocked by: Slice 1

Import equipment status sheets into equipment master/current snapshot records. This slice gives the planning engine equipment availability and current-state evidence.

What it should demonstrate:

- equipment identity and source equipment name preservation
- domain and process grouping
- current WO/item/process fields when available
- normalized availability flag while preserving source status and notes

User stories covered:

- 11, 12

PRD acceptance criteria covered:

- 10, 11

Exit criteria:

- Equipment snapshot fixtures separate stable equipment identity from current status.
- Unavailable equipment is normalized without losing source status text.
- Equipment remains scoped to its planning domain.
- Current WO/item fields are preserved for later planning explanations.

## Slice 5: Recipe Matching, Ambiguity, And T.B.D Report

Type: AFK
Blocked by: Slice 2, Slice 3

Match production-plan lines to recipe records within the same planning domain. Emit explicit missing, ambiguous, deprecated, and T.B.D-needed results.

What it should demonstrate:

- same-domain recipe lookup by item and recipe status
- no default cross-domain matching
- missing-recipe report for plan lines without valid candidates
- ambiguous-match report when multiple candidates exist
- deprecated recipe exclusion unless explicitly overridden later

User stories covered:

- 6, 7, 8, 9, 13

PRD acceptance criteria covered:

- 5, 6, 7, 8, 9

Exit criteria:

- STS plan lines do not auto-match Hydraulic (`유압`) historical recipes.
- Missing recipe lines become T.B.D report rows.
- Ambiguous candidates are visible instead of silently selected.
- Deprecated recipes are not selected by default.

## Slice 6: Load Summary And Bottleneck-Risk Proxy

Type: AFK
Blocked by: Slice 4, Slice 5

Generate rough load summaries and bottleneck-risk indicators without pretending that standard times exist. This slice creates useful planning signals from recipe steps, quantities, weights, and equipment availability.

What it should demonstrate:

- load by planning domain, process group, equipment group, and recipe step
- rough bottleneck-risk indicators
- shortest lead-time proxy labels and explanation fields
- unplannable line reporting for missing recipe, missing equipment, or invalid domain data

User stories covered:

- 14, 15, 18

PRD acceptance criteria covered:

- 11, 12, 16, 17

Exit criteria:

- Outputs are clearly labeled as proxy results when standard times are absent.
- Load summaries aggregate only after domain-specific recipe matching.
- Equipment unavailability affects bottleneck-risk output.
- Reports include missing, ambiguous, and unplannable counts.

## Slice 7: User-Authored Scenario Comparison

Type: AFK
Blocked by: Slice 6

Normalize user-authored scenario workbook inputs and compare scenarios with deterministic metrics. This is the first end-to-end planning MVP slice.

What it should demonstrate:

- scenario header, rules, equipment overrides, priority overrides, recipe overrides, and output requests
- built-in scenario templates such as shortest lead-time proxy, heavy-weight-first, customer-priority, equipment-unavailable, and bottleneck-avoidance
- deterministic scenario comparison ranking with reason signals
- separation between AI-drafted scenario suggestions and user-confirmed executable scenarios

User stories covered:

- 16, 17, 18, 19

PRD acceptance criteria covered:

- 13, 14, 15, 16, 17

Exit criteria:

- Invalid scenario workbook rows are reported before execution.
- AI-drafted scenarios are not executable until user confirmation.
- The same normalized inputs and engine version produce the same scenario ranking.
- Scenario comparison shows ranking plus missing recipe count, ambiguous recipe count, unplannable count, load summaries, bottleneck-risk signals, and ranking reasons.

## Dependency Order

1. Slice 1: Normalized Planning Contracts And Fixture Harness
2. Slice 2: Production Plan Import And Validation
3. Slice 3: Historical Work-Order Import And Recipe Candidate Extraction
4. Slice 4: Equipment Snapshot Import
5. Slice 5: Recipe Matching, Ambiguity, And T.B.D Report
6. Slice 6: Load Summary And Bottleneck-Risk Proxy
7. Slice 7: User-Authored Scenario Comparison

Slices 2, 3, and 4 can proceed in parallel after Slice 1. Slice 5 requires plan and recipe inputs. Slice 6 requires equipment and matching outputs. Slice 7 completes the first end-to-end comparison workflow.

## Published As GitHub Issues

Published on 2026-07-01 after user approval:

- #16: Normalized Planning Contracts And Fixture Harness
- #17: Production Plan Import And Validation
- #18: Historical Work-Order Import And Recipe Candidate Extraction
- #19: Equipment Snapshot Import
- #20: Recipe Matching, Ambiguity, And T.B.D Report
- #21: Load Summary And Bottleneck-Risk Proxy
- #22: User-Authored Scenario Comparison

Published issue details are tracked in `docs/prd/active/production-planning-issue-drafts.md`.

Each issue keeps the exit criteria translated into issue acceptance criteria.
