from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from .contracts import (
    EquipmentSnapshot,
    PlanningDomain,
    ProductionPlanLine,
    RecipeHeader,
    RecipeStep,
    ScenarioDefinition,
    WorkOrderOperation,
)
from .domains import DOMAIN_LABEL_BY_CODE, normalize_domain_code


@dataclass(frozen=True)
class PlanningFixtureSet:
    domains: tuple[PlanningDomain, ...] = field(default_factory=tuple)
    production_plan_lines: tuple[ProductionPlanLine, ...] = field(default_factory=tuple)
    work_order_operations: tuple[WorkOrderOperation, ...] = field(default_factory=tuple)
    equipment_snapshots: tuple[EquipmentSnapshot, ...] = field(default_factory=tuple)
    recipe_headers: tuple[RecipeHeader, ...] = field(default_factory=tuple)
    recipe_steps: tuple[RecipeStep, ...] = field(default_factory=tuple)
    scenario_definitions: tuple[ScenarioDefinition, ...] = field(default_factory=tuple)


def load_fixture_set(fixture_dir: str | Path) -> PlanningFixtureSet:
    root = Path(fixture_dir)
    return PlanningFixtureSet(
        domains=tuple(_domain_from_row(row) for row in _read_json_array(root / "domains.json")),
        production_plan_lines=tuple(
            _production_plan_line_from_row(row)
            for row in _read_json_array(root / "production_plan_lines.json")
        ),
        work_order_operations=tuple(
            _work_order_operation_from_row(row)
            for row in _read_json_array(root / "work_order_operations.json")
        ),
        equipment_snapshots=tuple(
            _equipment_snapshot_from_row(row)
            for row in _read_json_array(root / "equipment_snapshots.json")
        ),
        recipe_headers=tuple(
            _recipe_header_from_row(row)
            for row in _read_json_array(root / "recipe_headers.json")
        ),
        recipe_steps=tuple(
            _recipe_step_from_row(row)
            for row in _read_json_array(root / "recipe_steps.json")
        ),
        scenario_definitions=tuple(
            _scenario_definition_from_row(row)
            for row in _read_json_array(root / "scenario_definitions.json")
        ),
    )


def _domain_from_row(row: dict[str, Any]) -> PlanningDomain:
    domain_code = normalize_domain_code(row.get("domain_code") or row["source_value"])
    return PlanningDomain(
        domain_code=domain_code,
        domain_label=str(row.get("domain_label") or DOMAIN_LABEL_BY_CODE[domain_code]),
        substitution_policy=str(row["substitution_policy"]),
        source_value=str(row["source_value"]),
    )


def _production_plan_line_from_row(row: dict[str, Any]) -> ProductionPlanLine:
    return ProductionPlanLine(
        plan_batch_id=str(row["plan_batch_id"]),
        plan_period=str(row["plan_period"]),
        plan_type=str(row["plan_type"]),
        domain_code=_domain_code_from_row(row),
        domain_label=str(
            row.get("domain_label")
            or row.get("domain_source")
            or row.get("domain_code")
            or ""
        ),
        customer_name=str(row["customer_name"]),
        customer_order_ref=str(row["customer_order_ref"]),
        order_type=str(row["order_type"]),
        product_group=str(row["product_group"]),
        item_code=str(row["item_code"]),
        item_name=str(row["item_name"]),
        order_quantity=float(row["order_quantity"]),
        weight=_optional_float(row.get("weight")),
        unit=str(row.get("unit", "")),
        source_row_id=str(row["source_row_id"]),
        raw_values=_dict(row.get("raw_values", {})),
    )


def _work_order_operation_from_row(row: dict[str, Any]) -> WorkOrderOperation:
    return WorkOrderOperation(
        import_batch_id=str(row["import_batch_id"]),
        operation_date=str(row.get("operation_date", "")),
        domain_code=_domain_code_from_row(row),
        shift_or_team=str(row.get("shift_or_team", "")),
        work_order_no=str(row["work_order_no"]),
        process_sequence=int(row["process_sequence"]),
        process_group=str(row["process_group"]),
        process_name=str(row["process_name"]),
        operation_sequence=int(row["operation_sequence"]),
        equipment_name=str(row.get("equipment_name", "")),
        item_code=str(row.get("item_code", "")),
        item_name=str(row.get("item_name", "")),
        instruction_quantity=_optional_float(row.get("instruction_quantity")),
        input_quantity=_optional_float(row.get("input_quantity")),
        output_quantity=_optional_float(row.get("output_quantity")),
        defect_quantity=_optional_float(row.get("defect_quantity")),
        unit=str(row.get("unit", "")),
        first_input_material=str(row.get("first_input_material", "")),
        source_row_id=str(row["source_row_id"]),
        raw_values=_dict(row.get("raw_values", {})),
    )


def _equipment_snapshot_from_row(row: dict[str, Any]) -> EquipmentSnapshot:
    return EquipmentSnapshot(
        snapshot_batch_id=str(row["snapshot_batch_id"]),
        snapshot_at=str(row["snapshot_at"]),
        domain_code=_domain_code_from_row(row),
        process_group=str(row["process_group"]),
        equipment_id=str(row["equipment_id"]),
        equipment_name=str(row["equipment_name"]),
        equipment_status=str(row["equipment_status"]),
        is_available=bool(row["is_available"]),
        unavailable_reason=str(row.get("unavailable_reason", "")),
        current_work_order_no=str(row.get("current_work_order_no", "")),
        current_process_sequence=str(row.get("current_process_sequence", "")),
        current_process_name=str(row.get("current_process_name", "")),
        current_item_code=str(row.get("current_item_code", "")),
        current_item_name=str(row.get("current_item_name", "")),
        elapsed_or_remaining_time=str(row.get("elapsed_or_remaining_time", "")),
        source_row_id=str(row["source_row_id"]),
        raw_values=_dict(row.get("raw_values", {})),
    )


def _recipe_header_from_row(row: dict[str, Any]) -> RecipeHeader:
    return RecipeHeader(
        domain_code=_domain_code_from_row(row),
        recipe_id=str(row["recipe_id"]),
        recipe_version=str(row["recipe_version"]),
        recipe_status=str(row["recipe_status"]),
        product_group=str(row.get("product_group", "")),
        item_code=str(row["item_code"]),
        item_name=str(row.get("item_name", "")),
        representative_spec=str(row.get("representative_spec", "")),
        first_input_material=str(row.get("first_input_material", "")),
        source_type=str(row.get("source_type", "")),
        source_import_batch_id=str(row.get("source_import_batch_id", "")),
        source_work_order_refs=_tuple(row.get("source_work_order_refs", [])),
        usage_count=int(row.get("usage_count", 0)),
        confidence=str(row.get("confidence", "")),
        last_observed_date=str(row.get("last_observed_date", "")),
        effective_from=str(row.get("effective_from", "")),
        effective_to=str(row.get("effective_to", "")),
        confirmed_by=str(row.get("confirmed_by", "")),
        confirmed_at=str(row.get("confirmed_at", "")),
        notes=str(row.get("notes", "")),
        source_row_id=str(row["source_row_id"]),
        raw_values=_dict(row.get("raw_values", {})),
    )


def _recipe_step_from_row(row: dict[str, Any]) -> RecipeStep:
    return RecipeStep(
        domain_code=_domain_code_from_row(row),
        recipe_id=str(row["recipe_id"]),
        recipe_version=str(row["recipe_version"]),
        step_no=int(row["step_no"]),
        process_group=str(row["process_group"]),
        process_name=str(row["process_name"]),
        process_code=str(row.get("process_code", "")),
        is_required=bool(row.get("is_required", True)),
        repeat_count=int(row.get("repeat_count", 1)),
        preferred_equipment=str(row.get("preferred_equipment", "")),
        alternate_equipment_names=_tuple(row.get("alternate_equipment_names", [])),
        input_basis=str(row.get("input_basis", "")),
        quantity_factor=float(row.get("quantity_factor", 1)),
        weight_factor=float(row.get("weight_factor", 0)),
        constraints=_dict(row.get("constraints", {})),
        notes=str(row.get("notes", "")),
        source_row_id=str(row["source_row_id"]),
        raw_values=_dict(row.get("raw_values", {})),
    )


def _scenario_definition_from_row(row: dict[str, Any]) -> ScenarioDefinition:
    return ScenarioDefinition(
        scenario_id=str(row["scenario_id"]),
        scenario_name=str(row["scenario_name"]),
        scenario_source=str(row["scenario_source"]),
        scope=str(row["scope"]),
        included_plan_batch_ids=_tuple(row.get("included_plan_batch_ids", [])),
        domain_filters=tuple(
            normalize_domain_code(value)
            for value in row.get("domain_filters", [])
        ),
        priority_rule=str(row["priority_rule"]),
        proxy_weights={
            str(key): float(value)
            for key, value in _dict(row.get("proxy_weights", {})).items()
        },
        equipment_overrides=_dict(row.get("equipment_overrides", {})),
        priority_overrides=_dict(row.get("priority_overrides", {})),
        recipe_overrides=_dict(row.get("recipe_overrides", {})),
        output_requirements=_tuple(row.get("output_requirements", [])),
        engine_version=str(row["engine_version"]),
        is_executable=bool(row["is_executable"]),
        source_row_id=str(row["source_row_id"]),
        raw_values=_dict(row.get("raw_values", {})),
    )


def _domain_code_from_row(row: dict[str, Any]) -> str:
    return normalize_domain_code(
        row.get("domain_code")
        or row.get("domain_source")
        or row.get("domain_label")
        or row.get("source_value")
        or ""
    )


def _optional_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    return float(value)


def _tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError("Fixture tuple fields must be JSON arrays.")
    return tuple(str(item) for item in value)


def _dict(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("Fixture mapping fields must be JSON objects.")
    return dict(value)


def _read_json_array(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path.name} must contain a JSON array.")
    return data
