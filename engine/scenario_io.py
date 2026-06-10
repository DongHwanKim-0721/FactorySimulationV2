from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any

from .models import Operator, OperatorAssignment, ProcessBlock, ProcessConnection, Scenario


LEGACY_BLOCK_TYPE_MAP = {
    "STORAGE": "WORK_WAITING",
    "STRAIGHTNESS": "INSPECTION",
    "PRESS": "CORRECTION",
}


@dataclass
class ScenarioSheet:
    name: str
    scenario: Scenario


@dataclass
class ScenarioDocument:
    sheets: list[ScenarioSheet] = field(default_factory=list)
    active_sheet_index: int = 0


def save(scenario: Scenario, path: str | Path) -> None:
    data = {
        "blocks": [
            {
                "id": block.id,
                "type": normalize_block_type(block.type),
                "x": block.x,
                "y": block.y,
                "process_time_per_ea": block.process_time_per_ea,
                "concurrent_capacity": block.concurrent_capacity,
                "product_name": block.product_name,
                "material_name": block.material_name,
                "input_quantity": block.input_quantity,
                "input_time": block.input_time,
                "unit_weight_kg_per_ea": block.unit_weight_kg_per_ea,
                "transport_capacity": block.transport_capacity,
                "transport_time": block.transport_time,
                "custom_name": block.custom_name,
                "route_block_ids": list(block.route_block_ids),
                "route_review_required": block.route_review_required,
                "equipment_number": block.equipment_number,
            }
            for block in scenario.blocks
        ],
        "connections": [
            _connection_to_data(connection)
            for connection in scenario.connections
        ],
        "operators": [
            {
                "id": operator.id,
                "name": operator.name,
                "x": operator.x,
                "y": operator.y,
                "qualified_process_types": sorted(operator.qualified_process_types),
            }
            for operator in scenario.operators
        ],
        "operator_assignments": [
            {
                "id": assignment.id,
                "operator_id": assignment.operator_id,
                "block_id": assignment.block_id,
            }
            for assignment in scenario.operator_assignments
        ],
    }

    Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def load(path: str | Path) -> Scenario:
    data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))

    scenario = Scenario(
        blocks=[
            ProcessBlock(
                id=block_data["id"],
                type=normalize_block_type(block_data["type"]),
                x=block_data["x"],
                y=block_data["y"],
                process_time_per_ea=block_data["process_time_per_ea"],
                concurrent_capacity=block_data["concurrent_capacity"],
                product_name=block_data.get("product_name", "제품"),
                material_name=block_data.get("material_name", "원자재"),
                input_quantity=block_data.get("input_quantity", 10),
                input_time=block_data.get("input_time", 0.0),
                unit_weight_kg_per_ea=block_data.get("unit_weight_kg_per_ea", 1.0),
                transport_capacity=block_data.get("transport_capacity", 1),
                transport_time=block_data.get("transport_time", 1.0),
                custom_name=block_data.get("custom_name", ""),
                route_block_ids=tuple(
                    int(block_id)
                    for block_id in block_data.get("route_block_ids", [])
                ),
                route_review_required=bool(
                    block_data.get("route_review_required", False)
                ),
                equipment_number=block_data.get("equipment_number"),
            )
            for block_data in data.get("blocks", [])
        ],
        connections=[
            _connection_from_data(connection_data)
            for connection_data in data.get("connections", [])
        ],
        operators=[
            Operator(
                id=operator_data["id"],
                name=operator_data["name"],
                x=operator_data["x"],
                y=operator_data["y"],
                qualified_process_types=set(
                    operator_data.get("qualified_process_types", [])
                ),
            )
            for operator_data in data.get("operators", [])
        ],
        operator_assignments=[
            OperatorAssignment(
                id=assignment_data["id"],
                operator_id=assignment_data["operator_id"],
                block_id=assignment_data["block_id"],
            )
            for assignment_data in data.get("operator_assignments", [])
        ],
    )
    scenario.ensure_equipment_numbers()
    return scenario


def normalize_block_type(block_type: str) -> str:
    return LEGACY_BLOCK_TYPE_MAP.get(block_type, block_type)


def save_document(document: ScenarioDocument, path: str | Path) -> None:
    if not document.sheets:
        raise ValueError("A scenario document must contain at least one sheet.")

    active_sheet_index = max(
        0,
        min(document.active_sheet_index, len(document.sheets) - 1),
    )
    data = {
        "format": "FactorySimulationWorkbook",
        "version": 1,
        "active_sheet_index": active_sheet_index,
        "sheets": [
            {
                "name": sheet.name,
                "scenario": _scenario_to_data(sheet.scenario),
            }
            for sheet in document.sheets
        ],
    }
    _write_json(data, path)


def load_document(path: str | Path) -> ScenarioDocument:
    data: dict[str, Any] = json.loads(Path(path).read_text(encoding="utf-8"))

    if "sheets" not in data:
        return ScenarioDocument(
            sheets=[ScenarioSheet(name="Sheet1", scenario=_scenario_from_data(data))],
            active_sheet_index=0,
        )

    sheets = [
        ScenarioSheet(
            name=str(sheet_data.get("name") or f"Sheet{index + 1}"),
            scenario=_scenario_from_data(sheet_data.get("scenario", {})),
        )
        for index, sheet_data in enumerate(data.get("sheets", []))
    ]
    if not sheets:
        sheets = [ScenarioSheet(name="Sheet1", scenario=Scenario())]

    active_sheet_index = data.get("active_sheet_index", 0)
    if not isinstance(active_sheet_index, int):
        active_sheet_index = 0
    active_sheet_index = max(0, min(active_sheet_index, len(sheets) - 1))

    return ScenarioDocument(sheets=sheets, active_sheet_index=active_sheet_index)


def _scenario_to_data(scenario: Scenario) -> dict[str, Any]:
    return {
        "blocks": [
            {
                "id": block.id,
                "type": normalize_block_type(block.type),
                "x": block.x,
                "y": block.y,
                "process_time_per_ea": block.process_time_per_ea,
                "concurrent_capacity": block.concurrent_capacity,
                "product_name": block.product_name,
                "material_name": block.material_name,
                "input_quantity": block.input_quantity,
                "input_time": block.input_time,
                "unit_weight_kg_per_ea": block.unit_weight_kg_per_ea,
                "transport_capacity": block.transport_capacity,
                "transport_time": block.transport_time,
                "custom_name": block.custom_name,
                "route_block_ids": list(block.route_block_ids),
                "route_review_required": block.route_review_required,
                "equipment_number": block.equipment_number,
            }
            for block in scenario.blocks
        ],
        "connections": [
            _connection_to_data(connection)
            for connection in scenario.connections
        ],
        "operators": [
            {
                "id": operator.id,
                "name": operator.name,
                "x": operator.x,
                "y": operator.y,
                "qualified_process_types": sorted(operator.qualified_process_types),
            }
            for operator in scenario.operators
        ],
        "operator_assignments": [
            {
                "id": assignment.id,
                "operator_id": assignment.operator_id,
                "block_id": assignment.block_id,
            }
            for assignment in scenario.operator_assignments
        ],
    }


def _scenario_from_data(data: dict[str, Any]) -> Scenario:
    scenario = Scenario(
        blocks=[
            ProcessBlock(**_block_kwargs(block_data))
            for block_data in data.get("blocks", [])
        ],
        connections=[
            _connection_from_data(connection_data)
            for connection_data in data.get("connections", [])
        ],
        operators=[
            Operator(
                id=operator_data["id"],
                name=operator_data["name"],
                x=operator_data["x"],
                y=operator_data["y"],
                qualified_process_types=set(
                    operator_data.get("qualified_process_types", [])
                ),
            )
            for operator_data in data.get("operators", [])
        ],
        operator_assignments=[
            OperatorAssignment(
                id=assignment_data["id"],
                operator_id=assignment_data["operator_id"],
                block_id=assignment_data["block_id"],
            )
            for assignment_data in data.get("operator_assignments", [])
        ],
    )
    scenario.ensure_equipment_numbers()
    return scenario


def _block_kwargs(block_data: dict[str, Any]) -> dict[str, Any]:
    kwargs = {
        "id": block_data["id"],
        "type": normalize_block_type(block_data["type"]),
        "x": block_data["x"],
        "y": block_data["y"],
    }
    for field_name in (
        "process_time_per_ea",
        "concurrent_capacity",
        "product_name",
        "material_name",
        "input_quantity",
        "input_time",
        "unit_weight_kg_per_ea",
        "transport_capacity",
        "transport_time",
        "custom_name",
        "route_review_required",
        "equipment_number",
    ):
        if field_name in block_data:
            kwargs[field_name] = block_data[field_name]
    if "route_block_ids" in block_data:
        kwargs["route_block_ids"] = tuple(
            int(block_id) for block_id in block_data.get("route_block_ids", [])
        )
    return kwargs


def _connection_to_data(connection: ProcessConnection) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": connection.id,
        "from": connection.from_block,
        "to": connection.to_block,
    }
    if connection.product_names:
        data["product_names"] = list(connection.product_names)
    if connection.material_names:
        data["material_names"] = list(connection.material_names)
    if connection.source_block_ids:
        data["source_block_ids"] = list(connection.source_block_ids)
    return data


def _connection_from_data(connection_data: dict[str, Any]) -> ProcessConnection:
    return ProcessConnection(
        id=connection_data["id"],
        from_block=connection_data["from"],
        to_block=connection_data["to"],
        product_names=_string_tuple(connection_data.get("product_names", [])),
        material_names=_string_tuple(connection_data.get("material_names", [])),
        source_block_ids=tuple(
            int(block_id) for block_id in connection_data.get("source_block_ids", [])
        ),
    )


def _string_tuple(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item) for item in value if str(item).strip())


def _write_json(data: dict[str, Any], path: str | Path) -> None:
    Path(path).write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
