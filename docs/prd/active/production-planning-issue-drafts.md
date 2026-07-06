# Production Planning Issue Drafts

Status: PUBLISHED / IMPLEMENTED
Updated: 2026-07-06
Parent PRD: `docs/prd/active/production-planning-pivot.md`
Source slices: `docs/prd/active/production-planning-mvp-slices.md`

## Purpose

This document records the MVP slices that were published to GitHub issues on 2026-07-01 and completed by 2026-07-06.

Use this document as the local planning record for the published implementation issues and their dependency order.

## Implementation Status

All seven production-planning MVP issues are closed/completed.

- #16: completed by PR #23.
- #17: completed by PR #24.
- #18: completed by PR #25.
- #19: completed by PR #26.
- #20: completed by PR #27.
- #21: completed by PR #28.
- #22: completed by PR #29.

The acceptance criteria below remain as the historical issue contract. Future issues should extend the completed planning-core baseline rather than editing these issue records in place.

## Published Issues

1. #16: Build Normalized Planning Contracts And Fixture Harness.
2. #17: Import And Validate Production Plans.
3. #18: Import Historical Work Orders And Extract Recipe Candidates.
4. #19: Import Equipment Snapshot.
5. #20: Match Recipes And Emit T.B.D Reports.
6. #21: Generate Load Summary And Bottleneck-Risk Proxy.
7. #22: Compare User-Authored Planning Scenarios.

## Review Decision

Review date: 2026-07-01

Decision: keep all seven draft issues as the first production-planning MVP package. The current granularity matches the durable data boundaries: normalized contracts, production-plan import, historical WO recipe candidates, equipment snapshots, recipe/T.B.D matching, proxy load/risk reports, and user-authored scenario comparison. Do not merge or split them before first publication.

All seven published issues remain AFK. Human review is still required before changing the product contract, but no draft needs to become a HITL implementation issue right now.

Draft Issues 2, 3, and 4 should remain separate and can be implemented in parallel after Draft Issue 1. They share the normalized contract and fixture harness, but they do not depend on one another. Publish them after Draft Issue 1 so later blocker references can use real issue numbers.

Draft Issue 1 must include both the fixture harness contract and minimal sample fixture files. The fixture set should anchor source-row traceability, raw source preservation, UTF-8 planning-domain labels for Hydraulic (`유압`), STS, and shaped-material (`이형재`), deterministic report snapshots, and no dependency on manual INPUT/canvas route data.

The drafts were published to GitHub after explicit user approval. They were published in dependency order, with Draft Issues 2, 3, and 4 marked as parallelizable after Draft Issue 1.

## Draft Issue 1: Build Normalized Planning Contracts And Fixture Harness

Type: AFK

GitHub issue: #16

## Parent

Production Planning Core Pivot PRD.

## What to build

Create the minimal planning-core contract surface and a fixture-driven verification harness. This slice should prove that FactorySimulation V2 can represent production-planning source data without depending on the frozen route/canvas prototype.

The implementation should normalize planning domain, production plan line, work-order operation, equipment snapshot, recipe header, recipe step, and scenario definition records. It should preserve source-row traceability, keep Korean planning-domain labels such as `유압` and `이형재`, expose stable normalized domain codes, and produce deterministic fixture/report snapshots.

## Acceptance criteria

- [ ] The planning core can represent `PlanningDomain`, `ProductionPlanLine`, `WorkOrderOperation`, `EquipmentSnapshot`, `RecipeHeader`, `RecipeStep`, and `ScenarioDefinition` records.
- [ ] Minimal sample fixture files exist for the core contract surfaces and can be loaded by the fixture harness.
- [ ] Planning-domain labels preserve `유압`, `STS`, and `이형재` while exposing normalized domain codes.
- [ ] Fixture loading preserves source-row traceability and raw source values where applicable.
- [ ] The same fixture input produces the same normalized objects and report snapshot every run.
- [ ] No implementation depends on manual INPUT routes or canvas route data from the frozen prototype.

## Blocked by

None - can start immediately.

## Draft Issue 2: Import And Validate Production Plans

Type: AFK

GitHub issue: #17

## Parent

Production Planning Core Pivot PRD.

## What to build

Import monthly and weekly production-plan rows into normalized `ProductionPlanLine` records. This issue focuses on demand input quality and validation, not recipe matching.

The importer should capture customer, flexible customer/order reference, order type, product group, item code, item name, quantity, weight, source row, and raw source fields. It should trim source headers and report invalid rows without failing the entire import.

## Acceptance criteria

- [ ] A monthly production-plan fixture imports with correct row count and aggregate quantity/weight totals.
- [ ] A weekly production-plan fixture can use the same normalized contract.
- [ ] Customer, flexible order reference, product group, item code, item name, quantity, weight, source row, and raw source fields are preserved.
- [ ] Informal customer/order references are accepted as flexible references and are not rejected as invalid PO numbers.
- [ ] Headers with leading or trailing whitespace still map to known fields.
- [ ] Invalid rows are reported clearly without crashing the whole import.

## Blocked by

- #16: Build Normalized Planning Contracts And Fixture Harness.

## Draft Issue 3: Import Historical Work Orders And Extract Recipe Candidates

Type: AFK

GitHub issue: #18

## Parent

Production Planning Core Pivot PRD.

## What to build

Import historical work-order operation rows and extract recipe candidates by planning domain and item. This issue creates candidate recipe headers and ordered steps from execution history, but does not yet select recipes for production-plan lines.

The implementation should reconstruct work-order routes by domain, item, work order, process sequence, and operation sequence. Candidate recipes should retain source work-order evidence, usage count, and last-observed metadata. Historical candidates must remain distinguishable from user-confirmed recipes.

## Acceptance criteria

- [ ] Historical work-order fixtures import into normalized operation records.
- [ ] Work-order routes are reconstructed by domain, item, work order, process sequence, and operation sequence.
- [ ] Candidate recipe headers and ordered recipe steps are produced from historical operation evidence.
- [ ] Candidate recipes retain source work-order references.
- [ ] Candidate recipes from one planning domain are not grouped with another planning domain.
- [ ] Missing standard times do not block candidate extraction.

## Blocked by

- #16: Build Normalized Planning Contracts And Fixture Harness.

## Draft Issue 4: Import Equipment Snapshot

Type: AFK

GitHub issue: #19

## Parent

Production Planning Core Pivot PRD.

## What to build

Import equipment status sheets into normalized equipment master/current snapshot records. This issue gives the planning engine equipment identity, domain/process grouping, availability, and current-state evidence.

The importer should preserve source equipment name, source status text, notes, current WO, current item, and current process fields when available. It should normalize availability without losing original status information.

## Acceptance criteria

- [ ] Equipment snapshot fixtures import into normalized equipment snapshot records.
- [ ] Stable equipment identity is separated from current status.
- [ ] Source equipment name, status text, notes, and current WO/item/process fields are preserved when available.
- [ ] Unavailable equipment is normalized into an availability flag without losing source status text.
- [ ] Equipment remains scoped to its planning domain.

## Blocked by

- #16: Build Normalized Planning Contracts And Fixture Harness.

## Draft Issue 5: Match Recipes And Emit T.B.D Reports

Type: AFK

GitHub issue: #20

## Parent

Production Planning Core Pivot PRD.

## What to build

Match production-plan lines to recipe records within the same planning domain. Emit explicit matched, missing, ambiguous, deprecated, and T.B.D-needed results.

This issue should prevent false feasibility by disallowing default cross-domain matching. Missing recipes should become T.B.D report rows. Ambiguous candidates should stay visible unless a deterministic tie-break or user override exists. Deprecated recipes should not be selected by default.

## Acceptance criteria

- [ ] Production-plan lines are matched only against recipes in the same planning domain by default.
- [ ] STS plan lines do not auto-match Hydraulic (`유압`) historical recipes.
- [ ] A plan line with no valid recipe emits a missing-recipe/T.B.D report entry.
- [ ] Multiple candidate recipes for one item/domain are reported as ambiguous unless a deterministic tie-break or user override exists.
- [ ] Deprecated recipes are not selected by default.
- [ ] Excel T.B.D recipe headers and steps can normalize into the same recipe contract used by historical candidates.

## Blocked by

- #17: Import And Validate Production Plans.
- #18: Import Historical Work Orders And Extract Recipe Candidates.

## Draft Issue 6: Generate Load Summary And Bottleneck-Risk Proxy

Type: AFK

GitHub issue: #21

## Parent

Production Planning Core Pivot PRD.

## What to build

Generate rough load summaries and bottleneck-risk indicators without pretending that standard times exist. This issue should produce useful planning signals from matched recipe steps, quantities, weights, and equipment availability.

Outputs should be clearly labeled as proxy results when standard times are absent. Whole-factory outputs may aggregate domains only after domain-specific recipe matching and load calculation.

## Acceptance criteria

- [ ] Load summaries are produced by planning domain, process group, equipment group, and recipe step.
- [ ] Bottleneck-risk indicators reflect proxy factors and equipment availability.
- [ ] Equipment marked unavailable in the snapshot or scenario override affects bottleneck-risk output.
- [ ] Outputs are labeled as shortest lead-time proxy results and are not presented as precise lead time.
- [ ] Whole-factory summaries aggregate only after domain-specific recipe matching and load calculation.
- [ ] Reports include missing recipe count, ambiguous recipe count, and unplannable line count.

## Blocked by

- #19: Import Equipment Snapshot.
- #20: Match Recipes And Emit T.B.D Reports.

## Draft Issue 7: Compare User-Authored Planning Scenarios

Type: AFK

GitHub issue: #22

## Parent

Production Planning Core Pivot PRD.

## What to build

Normalize user-authored scenario workbook inputs and compare scenarios with deterministic metrics. This issue is the first end-to-end planning MVP slice.

Scenario inputs should include scenario header, rules, equipment overrides, priority overrides, recipe overrides, and output requests. Built-in templates should cover shortest lead-time proxy, heavy-weight-first, customer-priority, equipment-unavailable, and bottleneck-avoidance scenarios. AI-drafted scenario suggestions must remain drafts until user confirmation.

## Acceptance criteria

- [ ] Scenario workbook inputs normalize into executable `ScenarioDefinition` records only after required fields are valid.
- [ ] Invalid scenario workbook rows are reported before execution.
- [ ] Built-in scenario templates exist for shortest lead-time proxy, heavy-weight-first, customer-priority, equipment-unavailable, and bottleneck-avoidance cases.
- [ ] AI-drafted scenarios are marked as drafts and are not executable until user confirmation.
- [ ] The same normalized inputs and engine version produce the same scenario ranking.
- [ ] Scenario comparison shows ranking plus missing recipe count, ambiguous recipe count, unplannable count, load summaries, bottleneck-risk signals, and ranking reasons.
- [ ] Scenario outputs separate deterministic metrics from AI explanations.

## Blocked by

- #21: Generate Load Summary And Bottleneck-Risk Proxy.

## Published Order

1. #16: Build Normalized Planning Contracts And Fixture Harness.
2. #17: Import And Validate Production Plans.
3. #18: Import Historical Work Orders And Extract Recipe Candidates.
4. #19: Import Equipment Snapshot.
5. #20: Match Recipes And Emit T.B.D Reports.
6. #21: Generate Load Summary And Bottleneck-Risk Proxy.
7. #22: Compare User-Authored Planning Scenarios.

Issues #17, #18, and #19 can be implemented in parallel after #16. Later issues were published after their blockers existed so the `Blocked by` sections could reference real issue numbers.

## Resolved Review Questions

- Seven issues is the right initial granularity; keep the package intact.
- Draft Issues 2, 3, and 4 stay separate for parallel AFK work after Draft Issue 1.
- No draft is marked HITL for first publication; product-contract changes and issue publication remain user-approved gates.
- Tests should live inside each draft's acceptance criteria instead of becoming separate follow-up issues for the first MVP package.
- Draft Issue 1 includes sample fixture files and the fixture harness contract.
- GitHub publication completed on 2026-07-01 as issues #16-#22.
