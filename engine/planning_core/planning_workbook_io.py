from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from posixpath import dirname, normpath
from typing import Any, Mapping
from urllib.parse import unquote
from xml.sax.saxutils import escape
from zipfile import BadZipFile, ZIP_DEFLATED, ZipFile
import xml.etree.ElementTree as ET

from .equipment_snapshot_import import import_equipment_snapshot_rows
from .load_risk import generate_load_and_risk_report
from .production_plan_import import import_production_plan_rows
from .recipe_matching import match_plan_lines_to_recipes
from .reports import render_planning_run_report_snapshot
from .scenario_planning import compare_scenario_reports, import_scenario_workbook_rows
from .tbd_recipe_import import import_tbd_recipe_rows
from .work_order_import import extract_recipe_candidates, import_work_order_operation_rows


XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
OFFICE_REL_NS = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
PACKAGE_REL_NS = "{http://schemas.openxmlformats.org/package/2006/relationships}"

PLANNING_WORKBOOK_SHEETS = {
    "production_plan_rows": "Production_Plan",
    "work_order_rows": "Work_Order_Operations",
    "equipment_rows": "Equipment_Snapshot",
    "tbd_recipe_header_rows": "TBD_Recipe_Headers",
    "tbd_recipe_step_rows": "TBD_Recipe_Steps",
    "scenario_header_rows": "Scenario_Header",
    "scenario_rule_rows": "Scenario_Rules",
    "scenario_equipment_override_rows": "Equipment_Overrides",
    "scenario_priority_override_rows": "Priority_Overrides",
    "scenario_recipe_override_rows": "Recipe_Overrides",
    "scenario_output_request_rows": "Output_Requests",
}

PLANNING_WORKBOOK_HEADERS = {
    PLANNING_WORKBOOK_SHEETS["production_plan_rows"]: (
        "source_row_id",
        "domain",
        "customer",
        "customer_order_ref",
        "order_type",
        "product_group",
        "item_code",
        "item_name",
        "order_quantity",
        "weight",
        "unit",
    ),
    PLANNING_WORKBOOK_SHEETS["work_order_rows"]: (
        "source_row_id",
        "operation_date",
        "domain",
        "shift",
        "work_order_no",
        "process_sequence",
        "process_group",
        "process_name",
        "operation_sequence",
        "equipment_name",
        "item_code",
        "item_name",
        "instruction_quantity",
        "input_quantity",
        "output_quantity",
        "defect_quantity",
        "unit",
        "first_input_material",
    ),
    PLANNING_WORKBOOK_SHEETS["equipment_rows"]: (
        "source_row_id",
        "domain",
        "process_group",
        "equipment_id",
        "equipment_name",
        "equipment_status",
        "unavailable_reason",
        "current_work_order_no",
        "current_process_sequence",
        "current_process_name",
        "current_item_code",
        "current_item_name",
        "elapsed_or_remaining_time",
    ),
    PLANNING_WORKBOOK_SHEETS["tbd_recipe_header_rows"]: (
        "source_row_id",
        "domain",
        "recipe_id",
        "recipe_version",
        "product_group",
        "item_code",
        "item_name",
        "representative_spec",
        "first_input_material",
        "source_work_order_refs",
        "last_observed_date",
        "notes",
    ),
    PLANNING_WORKBOOK_SHEETS["tbd_recipe_step_rows"]: (
        "source_row_id",
        "domain",
        "recipe_id",
        "recipe_version",
        "step_no",
        "process_group",
        "process_name",
        "process_code",
        "is_required",
        "repeat_count",
        "preferred_equipment",
        "alternate_equipment_names",
        "input_basis",
        "quantity_factor",
        "weight_factor",
        "constraints",
        "notes",
    ),
    PLANNING_WORKBOOK_SHEETS["scenario_header_rows"]: (
        "source_row_id",
        "scenario_id",
        "scenario_name",
        "scenario_source",
        "scope",
        "included_plan_batch_ids",
        "domain_filters",
    ),
    PLANNING_WORKBOOK_SHEETS["scenario_rule_rows"]: (
        "source_row_id",
        "scenario_id",
        "priority_rule",
        "proxy_weights",
    ),
    PLANNING_WORKBOOK_SHEETS["scenario_equipment_override_rows"]: (
        "source_row_id",
        "scenario_id",
        "equipment_id",
        "is_available",
    ),
    PLANNING_WORKBOOK_SHEETS["scenario_priority_override_rows"]: (
        "source_row_id",
        "scenario_id",
        "customer_name",
        "priority_boost",
    ),
    PLANNING_WORKBOOK_SHEETS["scenario_recipe_override_rows"]: (
        "source_row_id",
        "scenario_id",
        "domain",
        "item_code",
        "recipe_id",
    ),
    PLANNING_WORKBOOK_SHEETS["scenario_output_request_rows"]: (
        "source_row_id",
        "scenario_id",
        "output_requirement",
    ),
}

PLANNING_WORKBOOK_SAMPLE_ROWS = {
    PLANNING_WORKBOOK_SHEETS["production_plan_rows"]: (
        {
            "source_row_id": "plan-row-2",
            "domain": "HYDRAULIC",
            "customer": "Acme",
            "customer_order_ref": "ACME-JUL-01",
            "order_type": "domestic",
            "product_group": "CYLINDER",
            "item_code": "HYD-100",
            "item_name": "Hydraulic cylinder A",
            "order_quantity": "120",
            "weight": "3400.5",
            "unit": "EA",
        },
        {
            "source_row_id": "plan-row-3",
            "domain": "STS",
            "customer": "Beta Steel",
            "customer_order_ref": "STS-RUSH-01",
            "order_type": "export",
            "product_group": "PIPE",
            "item_code": "STS-200",
            "item_name": "STS pipe B",
            "order_quantity": "80",
            "weight": "2100",
            "unit": "EA",
        },
        {
            "source_row_id": "plan-row-4",
            "domain": "SHAPED_MATERIAL",
            "customer": "Gamma Profile",
            "customer_order_ref": "SHP-PILOT-01",
            "order_type": "pilot",
            "product_group": "PROFILE",
            "item_code": "SHP-300",
            "item_name": "Shaped profile C",
            "order_quantity": "30",
            "weight": "600",
            "unit": "EA",
        },
    ),
    PLANNING_WORKBOOK_SHEETS["work_order_rows"]: (
        {
            "source_row_id": "wo-row-2",
            "operation_date": "2026-06-25",
            "domain": "HYDRAULIC",
            "shift": "A",
            "work_order_no": "WO-HYD-001",
            "process_sequence": "10",
            "process_group": "CUTTING",
            "process_name": "Cut",
            "operation_sequence": "1",
            "equipment_name": "HYD-CUT-01",
            "item_code": "HYD-100",
            "item_name": "Hydraulic cylinder A",
            "instruction_quantity": "120",
            "input_quantity": "120",
            "output_quantity": "118",
            "defect_quantity": "2",
            "unit": "EA",
            "first_input_material": "SCM440",
        },
        {
            "source_row_id": "wo-row-3",
            "operation_date": "2026-06-25",
            "domain": "HYDRAULIC",
            "shift": "A",
            "work_order_no": "WO-HYD-001",
            "process_sequence": "20",
            "process_group": "MACHINING",
            "process_name": "Machine",
            "operation_sequence": "2",
            "equipment_name": "HYD-MCH-01",
            "item_code": "HYD-100",
            "item_name": "Hydraulic cylinder A",
            "instruction_quantity": "120",
            "input_quantity": "118",
            "output_quantity": "118",
            "defect_quantity": "0",
            "unit": "EA",
            "first_input_material": "SCM440",
        },
        {
            "source_row_id": "wo-row-4",
            "operation_date": "2026-06-26",
            "domain": "STS",
            "shift": "B",
            "work_order_no": "WO-STS-001",
            "process_sequence": "10",
            "process_group": "POLISHING",
            "process_name": "Polish",
            "operation_sequence": "1",
            "equipment_name": "STS-POL-01",
            "item_code": "STS-200",
            "item_name": "STS pipe B",
            "instruction_quantity": "80",
            "input_quantity": "80",
            "output_quantity": "80",
            "defect_quantity": "0",
            "unit": "EA",
            "first_input_material": "STS304",
        },
    ),
    PLANNING_WORKBOOK_SHEETS["equipment_rows"]: (
        {
            "source_row_id": "eq-row-2",
            "domain": "HYDRAULIC",
            "process_group": "CUTTING",
            "equipment_id": "HYD-CUT-01",
            "equipment_name": "HYD-CUT-01",
            "equipment_status": "AVAILABLE",
            "current_work_order_no": "WO-HYD-001",
            "current_process_sequence": "10",
            "current_process_name": "Cut",
            "current_item_code": "HYD-100",
            "current_item_name": "Hydraulic cylinder A",
            "elapsed_or_remaining_time": "02:10 elapsed",
        },
        {
            "source_row_id": "eq-row-3",
            "domain": "HYDRAULIC",
            "process_group": "MACHINING",
            "equipment_id": "HYD-MCH-01",
            "equipment_name": "HYD-MCH-01",
            "equipment_status": "AVAILABLE",
        },
        {
            "source_row_id": "eq-row-4",
            "domain": "STS",
            "process_group": "POLISHING",
            "equipment_id": "STS-POL-01",
            "equipment_name": "STS-POL-01",
            "equipment_status": "DOWN",
            "unavailable_reason": "scheduled maintenance",
        },
    ),
    PLANNING_WORKBOOK_SHEETS["tbd_recipe_header_rows"]: (
        {
            "source_row_id": "tbd-header-row-2",
            "domain": "SHAPED_MATERIAL",
            "recipe_id": "TBD-SHP-300",
            "recipe_version": "1",
            "product_group": "PROFILE",
            "item_code": "SHP-300",
            "item_name": "Shaped profile C",
            "representative_spec": "300C",
            "first_input_material": "AL6061",
            "notes": "planner draft",
        },
    ),
    PLANNING_WORKBOOK_SHEETS["tbd_recipe_step_rows"]: (
        {
            "source_row_id": "tbd-step-row-2",
            "domain": "SHAPED_MATERIAL",
            "recipe_id": "TBD-SHP-300",
            "recipe_version": "1",
            "step_no": "10",
            "process_group": "FORMING",
            "process_name": "Form",
            "process_code": "FRM",
            "repeat_count": "2",
            "preferred_equipment": "SHP-FRM-01",
            "alternate_equipment_names": "SHP-FRM-02; SHP-FRM-03",
            "input_basis": "EA",
            "quantity_factor": "1",
            "weight_factor": "0",
        },
        {
            "source_row_id": "tbd-step-row-3",
            "domain": "SHAPED_MATERIAL",
            "recipe_id": "TBD-SHP-300",
            "recipe_version": "1",
            "step_no": "20",
            "process_group": "CUTTING",
            "process_name": "Cut",
            "process_code": "CUT",
            "repeat_count": "1",
            "preferred_equipment": "SHP-CUT-01",
            "input_basis": "EA",
            "quantity_factor": "1",
            "weight_factor": "0",
        },
    ),
    PLANNING_WORKBOOK_SHEETS["scenario_header_rows"]: (
        {
            "source_row_id": "scenario-header-row-2",
            "scenario_id": "SCN-BASE",
            "scenario_name": "Baseline",
            "scenario_source": "USER_AUTHORED",
            "scope": "WHOLE_FACTORY",
            "included_plan_batch_ids": "PLAN-2026-07-M",
            "domain_filters": "HYDRAULIC;STS;SHAPED_MATERIAL",
        },
        {
            "source_row_id": "scenario-header-row-3",
            "scenario_id": "SCN-HYD-CUT-DOWN",
            "scenario_name": "Hydraulic cutter unavailable",
            "scenario_source": "USER_AUTHORED",
            "scope": "WHOLE_FACTORY",
            "included_plan_batch_ids": "PLAN-2026-07-M",
            "domain_filters": "HYDRAULIC;STS;SHAPED_MATERIAL",
        },
        {
            "source_row_id": "scenario-header-row-4",
            "scenario_id": "SCN-AI-DRAFT",
            "scenario_name": "AI draft review only",
            "scenario_source": "AI_DRAFT",
            "scope": "WHOLE_FACTORY",
            "included_plan_batch_ids": "PLAN-2026-07-M",
            "domain_filters": "HYDRAULIC;STS;SHAPED_MATERIAL",
        },
    ),
    PLANNING_WORKBOOK_SHEETS["scenario_rule_rows"]: (
        {
            "source_row_id": "scenario-rule-row-2",
            "scenario_id": "SCN-BASE",
            "priority_rule": "SHORTEST_LEAD_TIME_PROXY",
            "proxy_weights": "process_count=1;equipment_unavailable=3",
        },
        {
            "source_row_id": "scenario-rule-row-3",
            "scenario_id": "SCN-HYD-CUT-DOWN",
            "priority_rule": "EQUIPMENT_UNAVAILABLE",
            "proxy_weights": "equipment_unavailable=5;process_count=1",
        },
        {
            "source_row_id": "scenario-rule-row-4",
            "scenario_id": "SCN-AI-DRAFT",
            "priority_rule": "BOTTLENECK_AVOIDANCE",
            "proxy_weights": "bottleneck_risk=5",
        },
    ),
    PLANNING_WORKBOOK_SHEETS["scenario_equipment_override_rows"]: (
        {
            "source_row_id": "scenario-equipment-row-2",
            "scenario_id": "SCN-HYD-CUT-DOWN",
            "equipment_id": "HYD-CUT-01",
            "is_available": "false",
        },
    ),
    PLANNING_WORKBOOK_SHEETS["scenario_priority_override_rows"]: (
        {
            "source_row_id": "scenario-priority-row-2",
            "scenario_id": "SCN-BASE",
            "customer_name": "Acme",
            "priority_boost": "1",
        },
    ),
    PLANNING_WORKBOOK_SHEETS["scenario_recipe_override_rows"]: (),
    PLANNING_WORKBOOK_SHEETS["scenario_output_request_rows"]: (
        {"scenario_id": "SCN-BASE", "output_requirement": "LOAD_SUMMARY"},
        {"scenario_id": "SCN-BASE", "output_requirement": "BOTTLENECK_RISK_REPORT"},
        {"scenario_id": "SCN-HYD-CUT-DOWN", "output_requirement": "LOAD_SUMMARY"},
        {
            "scenario_id": "SCN-HYD-CUT-DOWN",
            "output_requirement": "BOTTLENECK_RISK_REPORT",
        },
    ),
}

REPORT_WORKBOOK_SHEETS = {
    "run_metadata": "Run_Metadata",
    "recipe_matching": "Recipe_Matching",
    "tbd_report": "TBD_Report",
    "load_summary": "Load_Summary",
    "bottleneck_risk": "Bottleneck_Risk",
    "scenario_comparison": "Scenario_Comparison",
}

REPORT_WORKBOOK_HEADERS = {
    REPORT_WORKBOOK_SHEETS["run_metadata"]: ("key", "value"),
    REPORT_WORKBOOK_SHEETS["recipe_matching"]: (
        "plan_source_row_id",
        "domain_code",
        "item_code",
        "status",
        "selected_recipe_id",
        "candidate_recipe_ids",
        "deprecated_recipe_ids",
        "tbd_recipe_ids",
        "reason",
    ),
    REPORT_WORKBOOK_SHEETS["tbd_report"]: (
        "plan_source_row_id",
        "plan_batch_id",
        "domain_code",
        "item_code",
        "item_name",
        "customer_name",
        "customer_order_ref",
        "reason",
    ),
    REPORT_WORKBOOK_SHEETS["load_summary"]: (
        "scenario_id",
        "domain_code",
        "process_group",
        "equipment_group",
        "recipe_id",
        "recipe_step_no",
        "plan_source_row_ids",
        "order_quantity_total",
        "weight_total",
        "proxy_load_units",
    ),
    REPORT_WORKBOOK_SHEETS["bottleneck_risk"]: (
        "scenario_id",
        "domain_code",
        "process_group",
        "equipment_group",
        "proxy_load_units",
        "risk_level",
        "risk_score",
        "signals",
    ),
    REPORT_WORKBOOK_SHEETS["scenario_comparison"]: (
        "rank",
        "scenario_id",
        "scenario_name",
        "priority_rule",
        "deterministic_score",
        "missing_recipe_count",
        "ambiguous_recipe_count",
        "unplannable_line_count",
        "risk_score_total",
        "bottleneck_risk_signals",
        "ranking_reasons",
        "ai_explanation",
    ),
}


@dataclass(frozen=True)
class PlanningWorkbookRows:
    production_plan_rows: tuple[dict[str, Any], ...]
    work_order_rows: tuple[dict[str, Any], ...]
    equipment_rows: tuple[dict[str, Any], ...]
    tbd_recipe_header_rows: tuple[dict[str, Any], ...]
    tbd_recipe_step_rows: tuple[dict[str, Any], ...]
    scenario_header_rows: tuple[dict[str, Any], ...]
    scenario_rule_rows: tuple[dict[str, Any], ...]
    scenario_equipment_override_rows: tuple[dict[str, Any], ...]
    scenario_priority_override_rows: tuple[dict[str, Any], ...]
    scenario_recipe_override_rows: tuple[dict[str, Any], ...]
    scenario_output_request_rows: tuple[dict[str, Any], ...]


@dataclass(frozen=True)
class PlanningWorkbookRunConfig:
    plan_batch_id: str
    plan_period: str
    plan_type: str
    work_order_import_batch_id: str
    equipment_snapshot_batch_id: str
    equipment_snapshot_at: str
    tbd_import_batch_id: str
    engine_version: str


class PlanningWorkbookError(ValueError):
    pass


class PlanningWorkbookValidationError(ValueError):
    def __init__(self, errors_by_stage: Mapping[str, tuple[object, ...]]) -> None:
        self.errors_by_stage = {
            stage: tuple(errors)
            for stage, errors in errors_by_stage.items()
            if errors
        }
        super().__init__(self._message())

    def _message(self) -> str:
        counts = ", ".join(
            f"{stage}={len(errors)}"
            for stage, errors in sorted(self.errors_by_stage.items())
        )
        return f"Planning workbook validation failed: {counts}"


def load_planning_workbook_rows(workbook_path: str | Path) -> PlanningWorkbookRows:
    sheet_rows = load_xlsx_sheet_rows(workbook_path)
    missing_sheet_names = [
        sheet_name
        for sheet_name in PLANNING_WORKBOOK_SHEETS.values()
        if sheet_name not in sheet_rows
    ]
    if missing_sheet_names:
        raise PlanningWorkbookError(
            "Planning workbook is missing required sheet(s): "
            + ", ".join(sorted(missing_sheet_names))
        )

    return PlanningWorkbookRows(
        production_plan_rows=sheet_rows[PLANNING_WORKBOOK_SHEETS["production_plan_rows"]],
        work_order_rows=sheet_rows[PLANNING_WORKBOOK_SHEETS["work_order_rows"]],
        equipment_rows=sheet_rows[PLANNING_WORKBOOK_SHEETS["equipment_rows"]],
        tbd_recipe_header_rows=sheet_rows[
            PLANNING_WORKBOOK_SHEETS["tbd_recipe_header_rows"]
        ],
        tbd_recipe_step_rows=sheet_rows[
            PLANNING_WORKBOOK_SHEETS["tbd_recipe_step_rows"]
        ],
        scenario_header_rows=sheet_rows[
            PLANNING_WORKBOOK_SHEETS["scenario_header_rows"]
        ],
        scenario_rule_rows=sheet_rows[
            PLANNING_WORKBOOK_SHEETS["scenario_rule_rows"]
        ],
        scenario_equipment_override_rows=sheet_rows[
            PLANNING_WORKBOOK_SHEETS["scenario_equipment_override_rows"]
        ],
        scenario_priority_override_rows=sheet_rows[
            PLANNING_WORKBOOK_SHEETS["scenario_priority_override_rows"]
        ],
        scenario_recipe_override_rows=sheet_rows[
            PLANNING_WORKBOOK_SHEETS["scenario_recipe_override_rows"]
        ],
        scenario_output_request_rows=sheet_rows[
            PLANNING_WORKBOOK_SHEETS["scenario_output_request_rows"]
        ],
    )


def load_xlsx_sheet_rows(workbook_path: str | Path) -> dict[str, tuple[dict[str, Any], ...]]:
    return _read_xlsx_sheet_tables(Path(workbook_path))


def write_planning_workbook_template_xlsx(
    output_path: str | Path,
    *,
    include_examples: bool = True,
) -> None:
    rows = (
        PLANNING_WORKBOOK_SAMPLE_ROWS
        if include_examples
        else {
            sheet_name: ()
            for sheet_name in PLANNING_WORKBOOK_HEADERS
        }
    )
    _write_xlsx_sheet_tables(Path(output_path), rows, PLANNING_WORKBOOK_HEADERS)


def render_planning_workbook_report_snapshot(
    workbook_path: str | Path,
    *,
    config: PlanningWorkbookRunConfig,
) -> str:
    workbook_rows = load_planning_workbook_rows(workbook_path)

    plan_result = import_production_plan_rows(
        workbook_rows.production_plan_rows,
        plan_batch_id=config.plan_batch_id,
        plan_period=config.plan_period,
        plan_type=config.plan_type,
    )
    work_order_result = import_work_order_operation_rows(
        workbook_rows.work_order_rows,
        import_batch_id=config.work_order_import_batch_id,
    )
    equipment_result = import_equipment_snapshot_rows(
        workbook_rows.equipment_rows,
        snapshot_batch_id=config.equipment_snapshot_batch_id,
        snapshot_at=config.equipment_snapshot_at,
    )
    tbd_result = import_tbd_recipe_rows(
        workbook_rows.tbd_recipe_header_rows,
        workbook_rows.tbd_recipe_step_rows,
        import_batch_id=config.tbd_import_batch_id,
    )
    scenario_result = import_scenario_workbook_rows(
        header_rows=workbook_rows.scenario_header_rows,
        rule_rows=workbook_rows.scenario_rule_rows,
        equipment_override_rows=workbook_rows.scenario_equipment_override_rows,
        priority_override_rows=workbook_rows.scenario_priority_override_rows,
        recipe_override_rows=workbook_rows.scenario_recipe_override_rows,
        output_request_rows=workbook_rows.scenario_output_request_rows,
        engine_version=config.engine_version,
    )

    _raise_for_import_errors(
        {
            "production_plan": plan_result.errors,
            "work_orders": work_order_result.errors,
            "equipment_snapshot": equipment_result.errors,
            "tbd_recipes": tbd_result.errors,
            "scenarios": scenario_result.errors,
        }
    )

    recipe_candidates = extract_recipe_candidates(work_order_result.operations)
    recipe_headers = recipe_candidates.recipe_headers + tbd_result.recipe_headers
    recipe_steps = recipe_candidates.recipe_steps + tbd_result.recipe_steps
    matching_result = match_plan_lines_to_recipes(
        plan_result.lines,
        recipe_headers,
    )
    scenario_reports = {
        scenario.scenario_id: generate_load_and_risk_report(
            plan_lines=plan_result.lines,
            matching_result=matching_result,
            recipe_steps=recipe_steps,
            equipment_snapshots=equipment_result.snapshots,
            equipment_overrides=scenario.equipment_overrides,
        )
        for scenario in scenario_result.scenario_definitions
        if scenario.is_executable
    }
    scenario_comparison = compare_scenario_reports(
        scenarios=scenario_result.scenario_definitions,
        reports_by_scenario_id=scenario_reports,
        engine_version=config.engine_version,
    )

    return render_planning_run_report_snapshot(
        matching_result=matching_result,
        scenario_reports=scenario_reports,
        scenario_comparison=scenario_comparison,
    )


def write_planning_workbook_report_xlsx(
    workbook_path: str | Path,
    output_path: str | Path,
    *,
    config: PlanningWorkbookRunConfig,
) -> None:
    snapshot = render_planning_workbook_report_snapshot(workbook_path, config=config)
    write_planning_run_report_xlsx(snapshot, output_path)


def write_planning_run_report_xlsx(
    report_snapshot_json: str,
    output_path: str | Path,
) -> None:
    report = json.loads(report_snapshot_json)
    sheets = _report_workbook_rows(report)
    _write_xlsx_sheet_tables(Path(output_path), sheets, REPORT_WORKBOOK_HEADERS)


def _report_workbook_rows(report: Mapping[str, Any]) -> dict[str, tuple[dict[str, Any], ...]]:
    scenario_reports = report["scenario_reports"]
    scenario_comparison = report["scenario_comparison"]
    return {
        REPORT_WORKBOOK_SHEETS["run_metadata"]: _run_metadata_rows(report),
        REPORT_WORKBOOK_SHEETS["recipe_matching"]: tuple(
            dict(row) for row in report["recipe_matching"]["matches"]
        ),
        REPORT_WORKBOOK_SHEETS["tbd_report"]: tuple(
            dict(row) for row in report["recipe_matching"]["tbd_report_rows"]
        ),
        REPORT_WORKBOOK_SHEETS["load_summary"]: tuple(
            _with_scenario_id(scenario_id, row)
            for scenario_id, scenario_report in sorted(scenario_reports.items())
            for row in scenario_report["load_summary_rows"]
        ),
        REPORT_WORKBOOK_SHEETS["bottleneck_risk"]: tuple(
            _with_scenario_id(scenario_id, row)
            for scenario_id, scenario_report in sorted(scenario_reports.items())
            for row in scenario_report["bottleneck_risks"]
        ),
        REPORT_WORKBOOK_SHEETS["scenario_comparison"]: tuple(
            _scenario_comparison_export_row(row)
            for row in scenario_comparison["ranked_scenarios"]
        ),
    }


def _run_metadata_rows(report: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    scenario_comparison = report["scenario_comparison"]
    metadata = {
        "ai_role": report["ai_role"],
        "calculation_authority": report["calculation_authority"],
        "deferred_capabilities": report["deferred_capabilities"],
        "engine_version": scenario_comparison["engine_version"],
        "fixture_contract_version": report["fixture_contract_version"],
        "planning_boundary": report["planning_boundary"],
        "prototype_dependency": report["prototype_dependency"],
        "skipped_scenario_ids": scenario_comparison["skipped_scenario_ids"],
    }
    return tuple(
        {"key": key, "value": _cell_text(value)}
        for key, value in sorted(metadata.items())
    )


def _with_scenario_id(scenario_id: str, row: Mapping[str, Any]) -> dict[str, Any]:
    result = {"scenario_id": scenario_id}
    result.update(row)
    return result


def _scenario_comparison_export_row(row: Mapping[str, Any]) -> dict[str, Any]:
    metrics = row["deterministic_metrics"]
    return {
        "rank": row["rank"],
        "scenario_id": row["scenario_id"],
        "scenario_name": row["scenario_name"],
        "priority_rule": row["priority_rule"],
        "deterministic_score": row["deterministic_score"],
        "missing_recipe_count": row["missing_recipe_count"],
        "ambiguous_recipe_count": row["ambiguous_recipe_count"],
        "unplannable_line_count": row["unplannable_line_count"],
        "risk_score_total": metrics.get("risk_score_total", ""),
        "bottleneck_risk_signals": row["bottleneck_risk_signals"],
        "ranking_reasons": row["ranking_reasons"],
        "ai_explanation": row["ai_explanation"],
    }


def _raise_for_import_errors(errors_by_stage: Mapping[str, tuple[object, ...]]) -> None:
    if any(errors_by_stage.values()):
        raise PlanningWorkbookValidationError(errors_by_stage)


def _read_xlsx_sheet_tables(workbook_path: Path) -> dict[str, tuple[dict[str, Any], ...]]:
    try:
        with ZipFile(workbook_path) as archive:
            shared_strings = _read_shared_strings(archive)
            sheet_paths = _read_workbook_sheet_paths(archive)
            return {
                sheet_name: _read_sheet_table(archive, sheet_path, shared_strings)
                for sheet_name, sheet_path in sheet_paths.items()
            }
    except BadZipFile as exc:
        raise PlanningWorkbookError(
            f"Planning workbook is not a valid .xlsx file: {workbook_path}"
        ) from exc
    except KeyError as exc:
        raise PlanningWorkbookError(
            f"Planning workbook is missing required .xlsx part: {exc}"
        ) from exc
    except ET.ParseError as exc:
        raise PlanningWorkbookError(
            f"Planning workbook contains invalid worksheet XML: {workbook_path}"
        ) from exc


def _read_workbook_sheet_paths(archive: ZipFile) -> dict[str, str]:
    workbook_root = ET.fromstring(archive.read("xl/workbook.xml"))
    relationships_root = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
    relationships = {
        relationship.attrib["Id"]: _resolve_part_name(
            "xl/workbook.xml",
            relationship.attrib["Target"],
        )
        for relationship in relationships_root.findall(
            f"{PACKAGE_REL_NS}Relationship"
        )
    }

    sheet_paths: dict[str, str] = {}
    sheets = workbook_root.find(f"{XLSX_NS}sheets")
    if sheets is None:
        return sheet_paths
    for sheet in sheets.findall(f"{XLSX_NS}sheet"):
        relationship_id = sheet.attrib.get(f"{OFFICE_REL_NS}id")
        if relationship_id is None or relationship_id not in relationships:
            continue
        sheet_paths[sheet.attrib["name"]] = relationships[relationship_id]
    return sheet_paths


def _read_shared_strings(archive: ZipFile) -> tuple[str, ...]:
    if "xl/sharedStrings.xml" not in archive.namelist():
        return ()

    root = ET.fromstring(archive.read("xl/sharedStrings.xml"))
    strings: list[str] = []
    for shared_item in root.findall(f"{XLSX_NS}si"):
        strings.append("".join(text.text or "" for text in shared_item.iter(f"{XLSX_NS}t")))
    return tuple(strings)


def _read_sheet_table(
    archive: ZipFile,
    sheet_path: str,
    shared_strings: tuple[str, ...],
) -> tuple[dict[str, Any], ...]:
    root = ET.fromstring(archive.read(sheet_path))
    sheet_data = root.find(f"{XLSX_NS}sheetData")
    if sheet_data is None:
        return ()

    rows: list[dict[int, str]] = []
    for row in sheet_data.findall(f"{XLSX_NS}row"):
        row_values = _read_row_values(row, shared_strings)
        if _has_values(row_values):
            rows.append(row_values)

    if not rows:
        return ()

    headers = _header_by_column(rows[0])
    records: list[dict[str, Any]] = []
    for row_values in rows[1:]:
        if not any(
            str(row_values.get(column, "")).strip()
            for column in headers
        ):
            continue
        records.append(
            {
                header: row_values.get(column, "")
                for column, header in sorted(headers.items())
            }
        )
    return tuple(records)


def _read_row_values(row: ET.Element, shared_strings: tuple[str, ...]) -> dict[int, str]:
    values: dict[int, str] = {}
    next_column_index = 0
    for cell in row.findall(f"{XLSX_NS}c"):
        cell_reference = cell.attrib.get("r", "")
        column_index = (
            _column_index_from_cell_reference(cell_reference)
            if cell_reference
            else next_column_index
        )
        values[column_index] = _read_cell_value(cell, shared_strings)
        next_column_index = column_index + 1
    return values


def _read_cell_value(cell: ET.Element, shared_strings: tuple[str, ...]) -> str:
    cell_type = cell.attrib.get("t", "")
    if cell_type == "inlineStr":
        return "".join(text.text or "" for text in cell.iter(f"{XLSX_NS}t"))

    value = cell.find(f"{XLSX_NS}v")
    if value is None:
        return ""

    raw_value = value.text or ""
    if cell_type == "s":
        return shared_strings[int(raw_value)]
    if cell_type == "b":
        return "true" if raw_value == "1" else "false"
    return raw_value


def _header_by_column(row_values: Mapping[int, str]) -> dict[int, str]:
    headers: dict[int, str] = {}
    seen_headers: set[str] = set()
    for column, value in sorted(row_values.items()):
        header = str(value)
        if not header.strip():
            continue
        if header in seen_headers:
            raise PlanningWorkbookError(f"Duplicate workbook header: {header}")
        seen_headers.add(header)
        headers[column] = header
    return headers


def _has_values(row_values: Mapping[int, str]) -> bool:
    return any(str(value).strip() for value in row_values.values())


def _column_index_from_cell_reference(cell_reference: str) -> int:
    column_letters = "".join(
        char
        for char in cell_reference
        if "A" <= char.upper() <= "Z"
    )
    column_number = 0
    for char in column_letters.upper():
        column_number = (column_number * 26) + (ord(char) - ord("A") + 1)
    return column_number - 1


def _resolve_part_name(base_part_name: str, target: str) -> str:
    target = unquote(target).replace("\\", "/")
    if target.startswith("/"):
        return target.lstrip("/")
    return normpath(f"{dirname(base_part_name)}/{target}")


def _write_xlsx_sheet_tables(
    workbook_path: Path,
    sheets: Mapping[str, tuple[dict[str, Any], ...]],
    headers_by_sheet: Mapping[str, tuple[str, ...]],
) -> None:
    sheet_names = list(sheets.keys())
    with ZipFile(workbook_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml(len(sheet_names)))
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml(sheet_names))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml(sheet_names))

        for sheet_index, sheet_name in enumerate(sheet_names, start=1):
            archive.writestr(
                f"xl/worksheets/sheet{sheet_index}.xml",
                _worksheet_xml(
                    headers_by_sheet[sheet_name],
                    sheets[sheet_name],
                ),
            )


def _content_types_xml(sheet_count: int) -> str:
    overrides = "".join(
        (
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.worksheet+xml"/>'
        )
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.sheet.main+xml"/>'
        f"{overrides}"
        "</Types>"
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml(sheet_names: list[str]) -> str:
    sheets_xml = "".join(
        (
            f'<sheet name="{_xml_attr(sheet_name)}" sheetId="{index}" '
            f'r:id="rId{index}"/>'
        )
        for index, sheet_name in enumerate(sheet_names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheets_xml}</sheets>"
        "</workbook>"
    )


def _workbook_rels_xml(sheet_names: list[str]) -> str:
    relationships = "".join(
        (
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
        for index, _ in enumerate(sheet_names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{relationships}"
        "</Relationships>"
    )


def _worksheet_xml(
    headers: tuple[str, ...],
    rows: tuple[dict[str, Any], ...],
) -> str:
    row_xml = [_xlsx_row_xml(1, headers)]
    for row_index, row in enumerate(rows, start=2):
        row_xml.append(
            _xlsx_row_xml(row_index, tuple(row.get(header, "") for header in headers))
        )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(row_xml)}</sheetData>"
        "</worksheet>"
    )


def _xlsx_row_xml(row_index: int, values: tuple[Any, ...]) -> str:
    cells = "".join(
        _xlsx_cell_xml(row_index, column_index, value)
        for column_index, value in enumerate(values, start=1)
    )
    return f'<row r="{row_index}">{cells}</row>'


def _xlsx_cell_xml(row_index: int, column_index: int, value: Any) -> str:
    reference = f"{_column_name(column_index)}{row_index}"
    return (
        f'<c r="{reference}" t="inlineStr">'
        f"<is><t>{_xml_text(_cell_text(value))}</t></is>"
        "</c>"
    )


def _column_name(column_index: int) -> str:
    name = ""
    while column_index:
        column_index, remainder = divmod(column_index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name


def _cell_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (list, tuple)):
        return "; ".join(_cell_text(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    return str(value)


def _xml_text(value: Any) -> str:
    return escape("" if value is None else str(value))


def _xml_attr(value: Any) -> str:
    return escape(str(value), {'"': "&quot;"})
