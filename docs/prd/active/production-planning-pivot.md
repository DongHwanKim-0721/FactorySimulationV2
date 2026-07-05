# Production Planning Core Pivot PRD

Status: ACTIVE
Updated: 2026-07-06

## Problem Statement

FactorySimulation V2 currently works as a route/canvas Tkinter simulator, but the user's real planning need has shifted. The user does not primarily need to hand-draw raw-material routes on a canvas. The user needs to import monthly or weekly production plans, connect those plan lines to known or candidate recipes, account for equipment status, and compare production-planning scenarios.

The existing prototype should remain available as a reference and demo, but future product work needs a new production-planning core with clear data contracts.

## Solution

Build the next product around a deterministic production-planning core. The core should ingest production plans, historical work-order routing, equipment status snapshots, and Excel T.B.D recipe tables. It should produce recipe coverage, missing-recipe reports, work-center/process/equipment-group load summaries, bottleneck-risk indicators, and scenario comparisons.

The first implementation is data-model and engine first. UI work can come later. AI can help draft recipes, scenario ideas, and explanations, but deterministic logic must verify every calculation and comparison.

## Implementation Status

The first production-planning MVP package (#16-#22) is implemented and merged. The current core can normalize/import planning data, extract historical recipe candidates, import equipment snapshots, normalize Excel T.B.D recipe rows, match recipes by planning domain, generate proxy load/risk reports, normalize user-authored scenarios, and compare scenario reports deterministically.

The current stabilization target is an end-to-end planning-run report fixture. This report anchors the user-visible shape of the planning workflow before adding real Excel workbook IO, CLI commands, or a planning-core UI.

## Data Contracts

These contracts describe planning data, not a specific storage schema. Early importers may read pasted text, CSV, or Excel, but the deterministic engine should normalize all inputs into these concepts.

### PlanningDomain

Represents the planning work center. This is a first-class key, not a display-only field.

- `domain_code`: stable normalized code, such as `HYDRAULIC`, `STS`, or `SHAPED_MATERIAL`.
- `domain_label`: source-facing name, such as `유압`, `STS`, or `이형재`.
- `substitution_policy`: default is no cross-domain substitution.
- `source_value`: original imported work-center value.

### ProductionPlanLine

Represents one demand line from a monthly or weekly production plan.

- `plan_batch_id`: import batch identifier.
- `plan_period`: month or week represented by the source plan.
- `plan_type`: monthly or weekly.
- `domain_code`: normalized planning domain when known.
- `customer_name`: customer name from the plan.
- `customer_order_ref`: flexible customer/order reference, not restricted to formal PO numbers.
- `order_type`: source order type.
- `product_group`: source product group.
- `item_code`: item code used for recipe matching.
- `item_name`: source item name.
- `order_quantity`: planned quantity.
- `weight`: planned weight when available.
- `unit`: source unit when available.
- `source_row_id`: trace back to the imported row.
- `raw_values`: preserved raw source fields for audit and re-import debugging.

### WorkOrderOperation

Represents one operation row imported from historical work-order execution data.

- `import_batch_id`: historical import batch identifier.
- `operation_date`: source operation date when available.
- `domain_code`: normalized work center.
- `shift_or_team`: source shift/team value when available.
- `work_order_no`: work-order identifier.
- `process_sequence`: source process sequence.
- `process_group`: normalized process category.
- `process_name`: source process name.
- `operation_sequence`: operation row order within the work order.
- `equipment_name`: actual equipment used.
- `item_code`: item code when available.
- `item_name`: item name.
- `instruction_quantity`: planned or instructed quantity.
- `input_quantity`: input quantity.
- `output_quantity`: produced quantity.
- `defect_quantity`: defect quantity.
- `unit`: source unit.
- `first_input_material`: first input material when available.
- `source_row_id`: trace back to the imported row.

### EquipmentSnapshot

Represents equipment master/current state from an equipment status sheet.

- `snapshot_batch_id`: equipment snapshot import batch.
- `snapshot_at`: date/time or label of the snapshot.
- `domain_code`: normalized work center.
- `process_group`: process grouping for the equipment.
- `equipment_id`: stable equipment identifier when available.
- `equipment_name`: source equipment name.
- `equipment_status`: source status.
- `is_available`: normalized availability flag.
- `unavailable_reason`: reason or note when equipment is unavailable.
- `current_work_order_no`: current WO on the equipment when available.
- `current_process_sequence`: current process sequence when available.
- `current_process_name`: current process name when available.
- `current_item_code`: current item code when available.
- `current_item_name`: current item name when available.
- `elapsed_or_remaining_time`: source time field when available; not treated as standard time.
- `source_row_id`: trace back to the imported row.

### RecipeHeader

Represents a recipe identity and trust state.

- `domain_code`: normalized planning domain.
- `recipe_id`: stable recipe identifier.
- `recipe_version`: version for controlled changes.
- `recipe_status`: `AUTO_CANDIDATE`, `USER_CONFIRMED`, `TBD`, or `DEPRECATED`.
- `product_group`: product group.
- `item_code`: item code.
- `item_name`: item name.
- `representative_spec`: representative spec or size when available.
- `first_input_material`: first input material when available.
- `source_type`: historical WO, Excel T.B.D, manual confirmation, or migration.
- `source_import_batch_id`: import batch that created or updated the recipe.
- `source_work_order_refs`: historical work orders used as evidence.
- `usage_count`: number of observed matching historical routes.
- `confidence`: deterministic confidence band or score, if used.
- `last_observed_date`: latest historical observation.
- `effective_from`: start date for use when available.
- `effective_to`: end date when deprecated or superseded.
- `confirmed_by`: user or process that confirmed the recipe.
- `confirmed_at`: confirmation timestamp when available.
- `notes`: free-form remarks.

### RecipeStep

Represents one ordered process step in a recipe.

- `domain_code`: normalized planning domain.
- `recipe_id`: parent recipe identifier.
- `recipe_version`: parent recipe version.
- `step_no`: ordered step number; use gaps such as 10, 20, 30 for insertion.
- `process_group`: normalized process category.
- `process_name`: source process name.
- `process_code`: process code when available.
- `is_required`: whether the step is required.
- `repeat_count`: repeat count or pass count.
- `preferred_equipment`: preferred equipment when known.
- `alternate_equipment_names`: allowed alternatives within the same domain.
- `input_basis`: `EA`, `KG`, or `LOT`.
- `quantity_factor`: quantity-based load factor.
- `weight_factor`: weight-based load factor.
- `setup_time_min`: optional; may be blank in the first MVP.
- `time_basis`: optional; may remain blank until standard times exist.
- `constraints`: step-specific constraints.
- `notes`: free-form remarks.

### ScenarioDefinition

Represents a user-authored or AI-drafted comparison scenario after user confirmation.

- `scenario_id`: stable scenario identifier.
- `scenario_name`: user-facing name.
- `scenario_source`: user-authored, built-in, or AI-drafted-and-confirmed.
- `scope`: whole factory or one planning domain.
- `included_plan_batch_ids`: production-plan batches included.
- `domain_filters`: domains included or excluded.
- `priority_rule`: named rule such as shortest lead-time proxy, heavy-weight-first, or customer-priority.
- `proxy_weights`: explicit weights for lead-time proxy factors.
- `equipment_overrides`: availability or exclusion overrides.
- `priority_overrides`: customer, item, order, or product-group priority adjustments.
- `recipe_overrides`: recipe selection overrides for ambiguous items.
- `output_requirements`: reports requested by the scenario.
- `engine_version`: deterministic engine version used for reproducibility.

### Planning Outputs

The first planning engine should produce these outputs:

- `RecipeCoverageReport`: matched, missing, ambiguous, and deprecated recipe usage counts.
- `MissingRecipeReport`: plan lines requiring Excel T.B.D recipe work.
- `LoadSummary`: load by domain, process group, equipment group, and recipe step.
- `BottleneckRiskReport`: rough bottleneck indicators based on proxy factors and equipment status.
- `UnplannableLineReport`: lines blocked by missing recipes, missing equipment, or invalid domain data.
- `ScenarioComparison`: scenario-level ranking with explicit reasons and deterministic metrics.

## User Stories

1. As a production planner, I want to import a monthly production plan, so that planning starts from real demand lines instead of manual routes.
2. As a production planner, I want to import a weekly production plan, so that short-horizon planning can use the same core contract.
3. As a production planner, I want each plan line to preserve customer, item, quantity, and weight fields, so that scenario outputs can be traced back to source demand.
4. As a production planner, I want flexible customer/order references, so that informal PO-like values do not break import.
5. As a production planner, I want to bulk-import historical work-order routing, so that the system can discover candidate recipes from actual execution history.
6. As a production planner, I want recipe candidates grouped by work center and item, so that similar-looking items in different domains are not merged incorrectly.
7. As a production planner, I want to see which production-plan lines have no matching recipe, so that missing planning knowledge becomes explicit work.
8. As a production planner, I want to add missing recipes through an Excel T.B.D recipe table, so that incomplete DB coverage can be resolved outside the UI.
9. As a production planner, I want to distinguish auto-extracted, user-confirmed, T.B.D, and deprecated recipes, so that recipe trust is visible.
10. As a production planner, I want recipe versions, source import batch, usage count, confidence, and last-observed date, so that old or weak recipe candidates can be reviewed.
11. As a production planner, I want equipment status sheets imported as equipment master/current snapshots, so that planning reflects available and occupied equipment.
12. As a production planner, I want Hydraulic (`유압`), STS, and shaped-material (`이형재`) work centers handled separately, so that equipment and recipe matching stays realistic.
13. As a production planner, I want cross-work-center substitution disabled by default, so that the system does not invent false feasibility.
14. As a production planner, I want shortest lead-time proxy ranking before standard times exist, so that early scenario comparison is still useful without pretending precision.
15. As a production planner, I want the proxy to consider process count, repeated processes, bottleneck equipment, equipment availability, historical route similarity, quantity, and weight, so that ranking reflects practical constraints.
16. As a production planner, I want to define my own comparison scenarios, so that the system can reflect actual planning conversations.
17. As a production planner, I want built-in scenario examples, so that I can start from shortest lead-time, heavy-weight-first, customer-priority, equipment-unavailable, or bottleneck-avoidance assumptions.
18. As a production planner, I want scenario outputs to show missing recipes, unplannable lines, load summaries, and bottleneck risks, so that I can compare options without trusting a black box.
19. As a production planner, I want AI-generated recommendations clearly separated from deterministic results, so that I know which outputs are calculated facts and which are suggestions.
20. As a future developer, I want the route/canvas prototype marked as reference, so that I do not accidentally extend the old manual-route model as the new product.

## Scenario Contract

Scenario authoring should be Excel-first in the initial product direction. Users should be able to write or edit scenario inputs in a workbook, and the deterministic engine should normalize that workbook into `ScenarioDefinition` records.

Recommended scenario workbook sheets:

- `Scenario_Header`: scenario id, name, source, scope, included plan batches, included domains, and notes.
- `Scenario_Rules`: priority rule, proxy factors, proxy weights, and tie-break order.
- `Equipment_Overrides`: equipment availability changes, planned downtime, forced exclusions, and notes.
- `Priority_Overrides`: customer, order reference, product group, item, quantity, or weight priority boosts.
- `Recipe_Overrides`: forced recipe version choices for ambiguous items.
- `Output_Requests`: requested reports and comparison views.

Built-in scenario templates should include:

- shortest lead-time proxy
- heavy-weight-first
- customer-priority
- specific equipment unavailable
- process bottleneck avoidance
- domain-specific scenario rules

Rules for scenario execution:

- A scenario is not executable until required fields are valid after normalization.
- AI-drafted scenarios must be marked as drafts until the user confirms them.
- The same normalized inputs and engine version must produce the same outputs.
- Scenario comparison must show both the ranking and the reason signals behind the ranking.
- Scenario outputs must separate deterministic metrics from AI explanations.
- Whole-factory scenarios may aggregate domains, but matching and load calculation must still decompose by planning domain.

## Implementation Decisions

- Create a planning-domain model that treats Hydraulic (`유압`), STS, and shaped-material (`이형재`) work centers as first-class domains.
- Create import contracts for monthly/weekly production plans, historical work-order routing, equipment status snapshots, and Excel T.B.D recipe workbooks.
- Use production plan lines, recipe records, work-order-derived recipe candidates, and equipment snapshots as the future planning source of truth.
- Keep the existing route/canvas simulator frozen as a reference implementation and demo, not as the new planning input model.
- Separate the planning core into deep modules for import normalization, recipe catalog, equipment snapshot catalog, scenario normalization, deterministic planning, and report generation.
- Track recipe status values such as AUTO_CANDIDATE, USER_CONFIRMED, TBD, and DEPRECATED.
- Track recipe version, source work order or import batch, work center, usage count or confidence, last observed date, and confirmation status.
- Model missing recipes as explicit T.B.D outputs and Excel-ingestible recipe records.
- Support user-authored scenario definitions as first-class planning inputs.
- Use deterministic logic for import normalization, recipe matching, missing-recipe detection, load summaries, bottleneck-risk scoring, and scenario comparison.
- Allow AI only as an assistant for drafts, explanations, candidate review, and recommendations.
- Defer due-date scheduling and standard-time calculations until later phases.
- Prefer a data/engine-first implementation before building a new UI.

## MVP Acceptance Criteria

1. Given a monthly production plan import, the system preserves customer, flexible order reference, item code, item name, quantity, weight, source row, and raw source fields.
2. Given source headers with leading or trailing whitespace, import normalization still maps known fields correctly.
3. Given informal customer/order reference values, the import treats them as flexible references and does not reject them as invalid PO numbers.
4. Given historical work-order operation rows, the system reconstructs candidate recipe steps by domain, item, work order, process sequence, and equipment evidence.
5. Given STS production-plan lines and only Hydraulic (`유압`) historical recipes, the system does not auto-match those recipes across domains.
6. Given a plan line with no confirmed or candidate recipe in its planning domain, the system emits a missing-recipe/T.B.D report entry.
7. Given an Excel T.B.D recipe workbook, the system can normalize recipe headers and steps into the same recipe contract used by historical candidates.
8. Given multiple candidate recipes for one item/domain, the system marks the match as ambiguous unless a deterministic tie-break or user override exists.
9. Given deprecated recipes, the system does not select them by default for new planning unless the scenario explicitly overrides recipe selection.
10. Given an equipment snapshot, the system separates equipment master identity from current availability/status.
11. Given equipment marked unavailable in the snapshot or scenario override, the system reflects that in load and bottleneck-risk outputs.
12. Given no standard process times, the system labels ranking as shortest lead-time proxy and does not present it as precise lead time.
13. Given the same normalized data, scenario definition, and engine version, the system produces the same scenario outputs every time.
14. Given a user-authored scenario workbook, the system validates required fields before execution and reports invalid rows clearly.
15. Given AI-drafted recipe or scenario suggestions, the system marks them as suggestions or drafts until user confirmation.
16. Given whole-factory scenario comparison, the output aggregates domains only after domain-specific recipe matching and load calculation.
17. Given any scenario comparison, the output includes missing recipe count, ambiguous recipe count, unplannable line count, load summaries, bottleneck-risk signals, and ranking reasons.
18. Given the frozen route/canvas prototype docs, future planning-core implementation does not depend on manual INPUT routes as the monthly/weekly planning source of truth.

## Testing Decisions

- Tests should validate external planning behavior: imported rows, normalized keys, recipe matching, missing-recipe reporting, domain separation, scenario comparison outputs, and deterministic repeatability.
- Import tests should include flexible customer/order references and headers with extra whitespace.
- Recipe tests should prove that auto candidates, confirmed recipes, T.B.D recipes, and deprecated recipes are treated differently.
- Planning-domain tests should prove that Hydraulic (`유압`), STS, and shaped-material (`이형재`) records do not mix unless a future explicit substitution rule allows it.
- Scenario tests should compare deterministic outputs for built-in and user-authored scenarios.
- Prototype route/canvas tests remain useful as regression coverage for the frozen demo, but they should not define the new planning-core behavior.

## Out of Scope

- Extending the manual route/canvas editor as the main product path.
- Rebuilding the Tkinter UI for the planning core in the first design pass.
- Precise due-date scheduling.
- Standard operation-time calculation.
- Automatic cross-work-center substitution.
- Treating AI recommendations as verified planning calculations.
- Closing or re-triaging existing GitHub issues without explicit user request.

## Further Notes

The first useful MVP now imports plan data, imports historical work-order routing, imports equipment status, builds recipe candidates, detects missing recipes, defines the Excel T.B.D recipe format, produces load and missing-recipe summaries, and compares simple user-defined scenarios.

The implementation sequence for that MVP is tracked in `docs/prd/active/production-planning-mvp-slices.md`.

Future PRD refinements should focus on the next user-facing run surface and should preserve the current out-of-scope boundaries for due-date scheduling, standard-time calculation, AI-as-calculation-truth, and route/canvas source-of-truth behavior.
