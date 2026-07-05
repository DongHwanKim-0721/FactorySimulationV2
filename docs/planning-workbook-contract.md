# Planning Workbook Contract

Status: ACTIVE
Updated: 2026-07-06

This document defines the first executable Excel workbook surface for the production-planning core. The input workbook feeds the deterministic planning pipeline that already imports plan rows, historical work orders, equipment snapshots, T.B.D recipes, and user-authored scenarios. The CLI can write either the deterministic JSON snapshot or a planner-facing Excel report workbook derived from that same snapshot.

The workbook does not introduce due-date scheduling, standard-time calculation, AI calculation authority, or route/canvas planning-source behavior.

## Workbook Sheets

Every workbook must contain these sheets:

- `Production_Plan`
- `Work_Order_Operations`
- `Equipment_Snapshot`
- `TBD_Recipe_Headers`
- `TBD_Recipe_Steps`
- `Scenario_Header`
- `Scenario_Rules`
- `Equipment_Overrides`
- `Priority_Overrides`
- `Recipe_Overrides`
- `Output_Requests`

The first non-empty row is treated as the header row. Later rows are converted into row dictionaries and passed to the existing importers. Header names are trimmed before alias matching.

## Required Columns

`Production_Plan`

Required: `domain`, `customer`, `item_code`, `item_name`, `order_quantity`

Optional: `source_row_id`, `customer_order_ref`, `order_type`, `product_group`, `weight`, `unit`

`Work_Order_Operations`

Required: `domain`, `work_order_no`, `process_sequence`, `process_group`, `process_name`, `operation_sequence`, `item_code`

Optional: `source_row_id`, `operation_date`, `shift`, `equipment_name`, `item_name`, `instruction_quantity`, `input_quantity`, `output_quantity`, `defect_quantity`, `unit`, `first_input_material`

`Equipment_Snapshot`

Required: `domain`, `process_group`, `equipment_id`, `equipment_name`, `equipment_status`

Optional: `source_row_id`, `unavailable_reason`, `notes`, `current_work_order_no`, `current_process_sequence`, `current_process_name`, `current_item_code`, `current_item_name`, `elapsed_or_remaining_time`

`TBD_Recipe_Headers`

Required: `domain`, `recipe_id`, `item_code`, `item_name`

Optional: `source_row_id`, `recipe_version`, `product_group`, `representative_spec`, `first_input_material`, `source_work_order_refs`, `last_observed_date`, `notes`

`TBD_Recipe_Steps`

Required: `domain`, `recipe_id`, `step_no`, `process_group`, `process_name`

Optional: `source_row_id`, `recipe_version`, `process_code`, `is_required`, `repeat_count`, `preferred_equipment`, `alternate_equipment_names`, `input_basis`, `quantity_factor`, `weight_factor`, `constraints`, `notes`

`Scenario_Header`

Required: `scenario_id`, `scenario_name`, `scenario_source`, `scope`

Optional: `source_row_id`, `included_plan_batch_ids`, `domain_filters`

`Scenario_Rules`

Required: `scenario_id`, `priority_rule`

Optional: `source_row_id`, `proxy_weights`

`Equipment_Overrides`

Optional rows. When a row is present, use `scenario_id`, `equipment_id`, and `is_available`.

`Priority_Overrides`

Optional rows. When a row is present, use `scenario_id`, `customer_name`, and `priority_boost`.

`Recipe_Overrides`

Optional rows. When a row is present, use `scenario_id`, `domain`, `item_code`, and `recipe_id`.

`Output_Requests`

Optional rows. When a row is present, use `scenario_id` and `output_requirement`.

## Domain Values

Use one of these normalized planning domains:

- `HYDRAULIC`
- `STS`
- `SHAPED_MATERIAL`

The current planning core keeps domain pools separate. Cross-domain substitution is not performed by default.

## Execution Config

The workbook holds planning rows. The deterministic run metadata is supplied by the caller so the same workbook can be re-run for different batches or snapshots.

Required CLI config:

- `--plan-batch-id`
- `--plan-period`
- `--plan-type`
- `--work-order-import-batch-id`
- `--equipment-snapshot-batch-id`
- `--equipment-snapshot-at`
- `--tbd-import-batch-id`
- `--engine-version`

## CLI Usage

Run a workbook and write the deterministic report JSON:

```powershell
python -m engine.planning_core.cli run-workbook .\planning-input.xlsx `
  --out .\planning-run-report.json `
  --plan-batch-id PLAN-2026-07-M `
  --plan-period 2026-07 `
  --plan-type MONTHLY `
  --work-order-import-batch-id WO-HISTORY-2026-06 `
  --equipment-snapshot-batch-id EQ-SNAPSHOT-2026-07-01 `
  --equipment-snapshot-at 2026-07-01T08:00:00 `
  --tbd-import-batch-id TBD-2026-07 `
  --engine-version planning-core-cli-v1
```

Use `--out -` to write the report JSON to stdout.

Run the same workbook and write an Excel report workbook:

```powershell
python -m engine.planning_core.cli run-workbook .\planning-input.xlsx `
  --out .\planning-run-report.xlsx `
  --plan-batch-id PLAN-2026-07-M `
  --plan-period 2026-07 `
  --plan-type MONTHLY `
  --work-order-import-batch-id WO-HISTORY-2026-06 `
  --equipment-snapshot-batch-id EQ-SNAPSHOT-2026-07-01 `
  --equipment-snapshot-at 2026-07-01T08:00:00 `
  --tbd-import-batch-id TBD-2026-07 `
  --engine-version planning-core-cli-v1
```

## Output Contract

When `--out` ends in `.json` or any non-`.xlsx` extension, the CLI writes the same deterministic planning-run report snapshot shape produced by `render_planning_run_report_snapshot`.

When `--out` ends in `.xlsx`, the CLI writes a report workbook with these sheets:

- `Run_Metadata`
- `Recipe_Matching`
- `TBD_Report`
- `Load_Summary`
- `Bottleneck_Risk`
- `Scenario_Comparison`

Both output formats include:

- recipe matching status counts and T.B.D report rows
- load summary rows
- bottleneck-risk proxy rows
- scenario comparison rankings
- skipped AI-draft scenario ids
- explicit `calculation_authority: DETERMINISTIC_ENGINE`
- explicit deferred capabilities for due-date scheduling and standard-time calculation

## Out Of Scope

- due-date scheduling
- standard-time calculation
- AI as calculation truth
- route/canvas prototype as planning source of truth
- changing the input workbook as part of report generation
