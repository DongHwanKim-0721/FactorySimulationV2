import json
import pytest
from pathlib import Path

from engine.models import Scenario
from engine.scenario_io import (
    ScenarioDocument,
    ScenarioSheet,
    load,
    load_document,
    save,
    save_document,
)
from engine.simulation import simulate


def test_scenario_rejects_duplicate_self_and_input_target_connections():
    scenario = Scenario()
    scenario.add_block("INPUT", x=0, y=0, material_name="A", input_quantity=10)
    scenario.add_block("CUTTING", x=200, y=0, process_time_per_ea=1)
    scenario.add_connection(1, 2)

    with pytest.raises(ValueError):
        scenario.add_connection(1, 2)

    with pytest.raises(ValueError):
        scenario.add_connection(1, 1)

    with pytest.raises(ValueError, match="원자재 투입 블록"):
        scenario.add_connection(2, 1)


def test_scenario_rejects_cycle_connections():
    scenario = Scenario()
    scenario.add_block("INPUT", x=0, y=0, material_name="A", input_quantity=10)
    scenario.add_block("CUTTING", x=200, y=0, process_time_per_ea=1)
    scenario.add_block("HEAT", x=400, y=0, process_time_per_ea=1)
    scenario.add_connection(1, 2)
    scenario.add_connection(2, 3)

    with pytest.raises(ValueError):
        scenario.add_connection(3, 2)


def test_delete_block_cascades_connections():
    scenario = Scenario()
    scenario.add_block("INPUT", x=0, y=0, material_name="A", input_quantity=10)
    scenario.add_block("CUTTING", x=200, y=0, process_time_per_ea=1)
    scenario.add_block("HEAT", x=400, y=0, process_time_per_ea=1)
    scenario.add_connection(1, 2)
    scenario.add_connection(2, 3)

    scenario.delete_block(2)

    assert [block.id for block in scenario.blocks] == [1, 3]
    assert scenario.connections == []


def test_blocks_auto_assign_equipment_numbers_by_type():
    scenario = Scenario()
    input_block = scenario.add_block("INPUT", x=0, y=0)
    first_cutting = scenario.add_block("CUTTING", x=100, y=0)
    second_cutting = scenario.add_block("CUTTING", x=200, y=0)
    heat = scenario.add_block("HEAT", x=300, y=0)

    assert input_block.equipment_number is None
    assert first_cutting.equipment_number == 1
    assert second_cutting.equipment_number == 2
    assert heat.equipment_number == 1


def test_duplicate_equipment_number_rejected_within_same_block_type():
    scenario = Scenario()
    scenario.add_block("CUTTING", x=0, y=0, equipment_number=1)

    with pytest.raises(ValueError, match="Duplicate equipment number"):
        scenario.add_block("CUTTING", x=100, y=0, equipment_number=1)

    scenario.add_block("HEAT", x=200, y=0, equipment_number=1)


def test_delete_block_removes_route_occurrences_and_marks_review_required():
    scenario = Scenario()
    input_block = scenario.add_block("INPUT", x=0, y=0, route_block_ids=(2, 3, 2))
    scenario.add_block("CUTTING", x=100, y=0, block_id=2)
    scenario.add_block("HEAT", x=200, y=0, block_id=3)

    scenario.delete_block(2)

    assert input_block.route_block_ids == (3,)
    assert input_block.route_review_required is True


def test_operator_assignment_validation_and_cascading_deletion():
    scenario = Scenario()
    scenario.add_block("INPUT", x=0, y=0, material_name="A", input_quantity=10)
    scenario.add_block("BENDING", x=200, y=0, process_time_per_ea=1)
    scenario.add_block("HOIST", x=400, y=0)
    scenario.add_block("WORK_WAITING", x=600, y=0)
    scenario.add_block("FREE", x=800, y=0)
    drawing_operator = scenario.add_operator(
        "Drawing",
        x=40,
        y=200,
        qualified_process_types={"DRAWING", "HEAT"},
    )
    bending_operator = scenario.add_operator(
        "Bending",
        x=180,
        y=200,
        qualified_process_types={"BENDING"},
    )

    scenario.add_operator_assignment(drawing_operator.id, 1)
    scenario.add_operator_assignment(drawing_operator.id, 3)
    scenario.add_operator_assignment(drawing_operator.id, 4)
    scenario.add_operator_assignment(drawing_operator.id, 5)

    with pytest.raises(ValueError, match="not qualified"):
        scenario.add_operator_assignment(drawing_operator.id, 2)

    scenario.add_operator_assignment(bending_operator.id, 2)

    with pytest.raises(ValueError, match="already has"):
        scenario.add_operator_assignment(drawing_operator.id, 2)

    scenario.delete_block(2)
    assert [assignment.block_id for assignment in scenario.operator_assignments] == [
        1,
        3,
        4,
        5,
    ]

    scenario.delete_operator(drawing_operator.id)
    assert scenario.operator_assignments == []


def test_save_load_roundtrip_then_simulate_bundle_scenario():
    scenario = Scenario()
    scenario.add_block(
        "INPUT",
        x=0,
        y=0,
        product_name="P1",
        material_name="A",
        input_quantity=10,
        input_time=5,
        unit_weight_kg_per_ea=2.5,
    )
    scenario.add_block(
        "CUTTING",
        x=200,
        y=0,
        process_time_per_ea=1,
        concurrent_capacity=1,
    )
    scenario.add_block(
        "HOIST",
        x=400,
        y=0,
        transport_capacity=4,
        transport_time=3,
    )
    scenario.add_connection(1, 2)
    scenario.add_connection(2, 3)

    path = Path("tests/.tmp_scenario.json")
    try:
        save(scenario, path)

        loaded = load(path)
        result = simulate(loaded.blocks, loaded.connections)

        assert loaded == scenario
        assert loaded.blocks[0].product_name == "P1"
        assert loaded.blocks[0].unit_weight_kg_per_ea == 2.5
        assert result.total_time == 24
        assert result.total_input_quantity == 10
        assert result.final_output_quantity == 10
    finally:
        path.unlink(missing_ok=True)


def test_save_load_roundtrip_preserves_routes_and_equipment_numbers():
    scenario = Scenario()
    scenario.add_block(
        "INPUT",
        x=0,
        y=0,
        product_name="P1",
        material_name="A",
        route_block_ids=(2, 2, 3),
        route_review_required=True,
    )
    scenario.add_block("CUTTING", x=200, y=0, block_id=2, equipment_number=7)
    scenario.add_block("HEAT", x=400, y=0, block_id=3, equipment_number=7)
    path = Path("tests/.tmp_route_scenario.json")

    try:
        save(scenario, path)
        saved = json.loads(path.read_text(encoding="utf-8"))
        loaded = load(path)

        assert saved["blocks"][0]["route_block_ids"] == [2, 2, 3]
        assert saved["blocks"][0]["route_review_required"] is True
        assert saved["blocks"][1]["equipment_number"] == 7
        assert loaded.blocks[0].route_block_ids == (2, 2, 3)
        assert loaded.blocks[0].route_review_required is True
        assert loaded.blocks[1].equipment_number == 7
        assert loaded.blocks[2].equipment_number == 7
    finally:
        path.unlink(missing_ok=True)


def test_save_load_roundtrip_preserves_operators_and_assignments():
    scenario = Scenario()
    scenario.add_block(
        "INPUT",
        x=0,
        y=0,
        product_name="P1",
        material_name="A",
        input_quantity=10,
    )
    scenario.add_block("CUTTING", x=200, y=0, process_time_per_ea=1)
    scenario.add_connection(1, 2)
    operator = scenario.add_operator(
        "Operator A",
        x=100,
        y=250,
        qualified_process_types={"CUTTING", "HEAT"},
    )
    scenario.add_operator_assignment(operator.id, 2)
    path = Path("tests/.tmp_operator_scenario.json")

    try:
        save(scenario, path)
        loaded = load(path)

        assert loaded.operators[0].id == operator.id
        assert loaded.operators[0].name == "Operator A"
        assert loaded.operators[0].x == 100
        assert loaded.operators[0].y == 250
        assert loaded.operators[0].qualified_process_types == {"CUTTING", "HEAT"}
        assert loaded.operator_assignments[0].operator_id == operator.id
        assert loaded.operator_assignments[0].block_id == 2
    finally:
        path.unlink(missing_ok=True)


def test_save_load_roundtrip_preserves_connection_routing_filters():
    scenario = Scenario()
    scenario.add_block(
        "INPUT",
        x=0,
        y=0,
        product_name="P1",
        material_name="A",
        input_quantity=10,
    )
    scenario.add_block("DRAWING", x=200, y=0)
    scenario.add_connection(
        1,
        2,
        product_names=("P1",),
        material_names=("A",),
        source_block_ids=(1,),
    )
    path = Path("tests/.tmp_connection_filters.json")

    try:
        save(scenario, path)
        saved = json.loads(path.read_text(encoding="utf-8"))
        loaded = load(path)

        assert saved["connections"][0]["product_names"] == ["P1"]
        assert saved["connections"][0]["material_names"] == ["A"]
        assert saved["connections"][0]["source_block_ids"] == [1]
        assert loaded.connections[0].product_names == ("P1",)
        assert loaded.connections[0].material_names == ("A",)
        assert loaded.connections[0].source_block_ids == (1,)
    finally:
        path.unlink(missing_ok=True)


def test_save_load_document_roundtrip_preserves_multiple_sheets():
    first = Scenario()
    first.add_block(
        "INPUT",
        x=0,
        y=0,
        product_name="P1",
        material_name="A",
        input_quantity=10,
    )

    second = Scenario()
    second.add_block(
        "INPUT",
        x=10,
        y=20,
        product_name="P2",
        material_name="B",
        input_quantity=5,
    )
    second.add_block("CUTTING", x=220, y=20, process_time_per_ea=2)
    second.add_connection(1, 2)

    path = Path("tests/.tmp_workbook.json")
    try:
        save_document(
            ScenarioDocument(
                sheets=[
                    ScenarioSheet(name="Line A", scenario=first),
                    ScenarioSheet(name="Line B", scenario=second),
                ],
                active_sheet_index=1,
            ),
            path,
        )

        saved = json.loads(path.read_text(encoding="utf-8"))
        loaded = load_document(path)

        assert saved["format"] == "FactorySimulationWorkbook"
        assert "last_result" not in saved["sheets"][0]
        assert loaded.active_sheet_index == 1
        assert [sheet.name for sheet in loaded.sheets] == ["Line A", "Line B"]
        assert loaded.sheets[0].scenario.blocks[0].product_name == "P1"
        assert loaded.sheets[1].scenario.connections[0].from_block == 1
        assert simulate(
            loaded.sheets[1].scenario.blocks,
            loaded.sheets[1].scenario.connections,
        ).final_output_quantity == 5
    finally:
        path.unlink(missing_ok=True)


def test_load_document_wraps_legacy_single_scenario_as_sheet1():
    path = Path("tests/.tmp_legacy_workbook.json")
    path.write_text(
        """
{
  "blocks": [
    {
      "id": 1,
      "type": "INPUT",
      "x": 0,
      "y": 0,
      "process_time_per_ea": 30.0,
      "concurrent_capacity": 1,
      "product_name": "P1",
      "material_name": "A",
      "input_quantity": 7,
      "input_time": 0
    }
  ],
  "connections": []
}
""",
        encoding="utf-8",
    )

    try:
        loaded = load_document(path)

        assert loaded.active_sheet_index == 0
        assert [sheet.name for sheet in loaded.sheets] == ["Sheet1"]
        assert loaded.sheets[0].scenario.blocks[0].input_quantity == 7
    finally:
        path.unlink(missing_ok=True)


def test_load_legacy_scenario_defaults_missing_product_name():
    path = Path("tests/.tmp_legacy_scenario.json")
    path.write_text(
        """
{
  "blocks": [
    {
      "id": 1,
      "type": "INPUT",
      "x": 0,
      "y": 0,
      "process_time_per_ea": 30.0,
      "concurrent_capacity": 1,
      "material_name": "A",
      "input_quantity": 10,
      "input_time": 0
    }
  ],
  "connections": []
}
""",
        encoding="utf-8",
    )

    try:
        loaded = load(path)

        assert loaded.blocks[0].product_name == "제품"
        assert loaded.blocks[0].unit_weight_kg_per_ea == 1.0
        assert loaded.operators == []
        assert loaded.operator_assignments == []
    finally:
        path.unlink(missing_ok=True)


def test_legacy_block_types_normalize_on_load_and_save():
    path = Path("tests/.tmp_legacy_types.json")
    normalized_path = Path("tests/.tmp_normalized_types.json")
    path.write_text(
        """
{
  "blocks": [
    {
      "id": 1,
      "type": "INPUT",
      "x": 10,
      "y": 20,
      "process_time_per_ea": 30.0,
      "concurrent_capacity": 1,
      "product_name": "P1",
      "material_name": "A",
      "input_quantity": 6,
      "input_time": 0
    },
    {
      "id": 2,
      "type": "STORAGE",
      "x": 210,
      "y": 20,
      "process_time_per_ea": 2,
      "concurrent_capacity": 2,
      "custom_name": "legacy storage"
    },
    {
      "id": 3,
      "type": "STRAIGHTNESS",
      "x": 410,
      "y": 20,
      "process_time_per_ea": 3,
      "concurrent_capacity": 1
    },
    {
      "id": 4,
      "type": "PRESS",
      "x": 610,
      "y": 20,
      "process_time_per_ea": 4,
      "concurrent_capacity": 1
    }
  ],
  "connections": [
    {"id": 1, "from": 1, "to": 2},
    {"id": 2, "from": 2, "to": 3},
    {"id": 3, "from": 3, "to": 4}
  ]
}
""",
        encoding="utf-8",
    )

    try:
        loaded = load(path)

        assert [block.type for block in loaded.blocks] == [
            "INPUT",
            "WORK_WAITING",
            "INSPECTION",
            "CORRECTION",
        ]
        assert loaded.blocks[1].id == 2
        assert loaded.blocks[1].x == 210
        assert loaded.blocks[1].process_time_per_ea == 2
        assert loaded.blocks[1].concurrent_capacity == 2
        assert loaded.blocks[1].custom_name == "legacy storage"
        assert [(item.from_block, item.to_block) for item in loaded.connections] == [
            (1, 2),
            (2, 3),
            (3, 4),
        ]

        result = simulate(loaded.blocks, loaded.connections)
        assert result.final_output_quantity == 6

        save(loaded, normalized_path)
        saved = json.loads(normalized_path.read_text(encoding="utf-8"))
        assert [block["type"] for block in saved["blocks"]] == [
            "INPUT",
            "WORK_WAITING",
            "INSPECTION",
            "CORRECTION",
        ]
    finally:
        path.unlink(missing_ok=True)
        normalized_path.unlink(missing_ok=True)


def test_save_normalizes_legacy_block_types_from_memory():
    scenario = Scenario()
    scenario.add_block("STORAGE", x=0, y=0, process_time_per_ea=5)
    scenario.add_block("PRESS", x=200, y=0, process_time_per_ea=7)
    path = Path("tests/.tmp_memory_legacy_types.json")

    try:
        save(scenario, path)
        saved = json.loads(path.read_text(encoding="utf-8"))

        assert [block["type"] for block in saved["blocks"]] == [
            "WORK_WAITING",
            "CORRECTION",
        ]
    finally:
        path.unlink(missing_ok=True)


def test_load_legacy_scenario_defaults_missing_route_and_equipment_fields():
    path = Path("tests/.tmp_legacy_route_fields.json")
    path.write_text(
        """
{
  "blocks": [
    {
      "id": 1,
      "type": "INPUT",
      "x": 0,
      "y": 0,
      "process_time_per_ea": 30.0,
      "concurrent_capacity": 1
    },
    {
      "id": 2,
      "type": "CUTTING",
      "x": 100,
      "y": 0,
      "process_time_per_ea": 45.0,
      "concurrent_capacity": 1
    }
  ],
  "connections": []
}
""",
        encoding="utf-8",
    )

    try:
        loaded = load(path)

        assert loaded.blocks[0].route_block_ids == ()
        assert loaded.blocks[0].route_review_required is False
        assert loaded.blocks[0].equipment_number is None
        assert loaded.blocks[1].equipment_number == 1
    finally:
        path.unlink(missing_ok=True)


def test_add_input_block_accepts_unit_weight():
    scenario = Scenario()

    block = scenario.add_block(
        "INPUT",
        x=0,
        y=0,
        unit_weight_kg_per_ea=3.25,
    )

    assert block.unit_weight_kg_per_ea == 3.25
