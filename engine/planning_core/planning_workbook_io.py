from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from posixpath import dirname, normpath
from typing import Any, Mapping
from urllib.parse import unquote
from zipfile import BadZipFile, ZipFile
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
    sheet_rows = _read_xlsx_sheet_tables(Path(workbook_path))
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
