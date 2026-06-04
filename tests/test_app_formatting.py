from app import (
    BLOCK_TYPES,
    CanvasView,
    PaletteView,
    build_monthly_input_choices,
    is_limited_number_input,
    format_monthly_input_choice,
    format_monthly_tons,
    format_flow_diagram,
    format_operator_qualification_summary,
    monthly_output_quantity_for_choice,
    realized_weekly_minutes_per_ea,
)
from engine.models import Operator, ProcessBlock, ProcessConnection
from engine.simulation import SimulationResult


def test_branch_join_flow_diagram_uses_actual_connections():
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=2),
        ProcessConnection(id=2, from_block=1, to_block=3),
        ProcessConnection(id=3, from_block=2, to_block=4),
        ProcessConnection(id=4, from_block=3, to_block=4),
    ]

    diagram = format_flow_diagram(
        process_flow=[1, 2, 3, 4],
        connections=connections,
        block_label=lambda block_id: f"B{block_id}",
    )

    assert diagram.splitlines() == [
        "B1 -> B2",
        "B1 -> B3",
        "B2 -> B4",
        "B3 -> B4",
    ]
    assert "B1 -> B2 -> B3 -> B4" not in diagram


def test_flow_diagram_lists_independent_blocks_without_fake_edges():
    diagram = format_flow_diagram(
        process_flow=[1, 2],
        connections=[],
        block_label=lambda block_id: f"B{block_id}",
    )

    assert diagram.splitlines() == ["B1", "B2"]


def test_operator_qualification_summary_counts_qualified_types():
    one_type = Operator(
        id=1,
        name="A",
        x=0,
        y=0,
        qualified_process_types={"CUTTING"},
    )
    two_types = Operator(
        id=2,
        name="B",
        x=0,
        y=0,
        qualified_process_types={"CUTTING", "HEAT"},
    )

    assert format_operator_qualification_summary(one_type) == "자격 1개"
    assert format_operator_qualification_summary(two_types) == "자격 2개"


def test_monthly_production_formatting_helpers_are_readable():
    block = ProcessBlock(
        id=3,
        type="INPUT",
        x=0,
        y=0,
        product_name="P1",
        material_name="A",
        unit_weight_kg_per_ea=2.5,
    )
    choice = build_monthly_input_choices([block])[0]

    assert format_monthly_input_choice(choice) == "P1/A (2.5 kg/EA)"
    assert format_monthly_tons(12) == "12 ton"
    assert format_monthly_tons(12.345) == "12.35 ton"


def test_monthly_input_choices_merge_same_material_name():
    choices = build_monthly_input_choices(
        [
            ProcessBlock(
                id=1,
                type="INPUT",
                x=0,
                y=0,
                product_name="P1",
                material_name="A",
                input_quantity=4,
                unit_weight_kg_per_ea=2,
            ),
            ProcessBlock(
                id=2,
                type="INPUT",
                x=0,
                y=0,
                product_name="P2",
                material_name="A",
                input_quantity=6,
                unit_weight_kg_per_ea=3,
            ),
            ProcessBlock(
                id=3,
                type="INPUT",
                x=0,
                y=0,
                product_name="P3",
                material_name="B",
                input_quantity=5,
                unit_weight_kg_per_ea=1,
            ),
        ]
    )

    assert [choice.material_name for choice in choices] == ["전체 원자재", "A", "B"]
    assert choices[0].is_total is True
    assert choices[0].block_ids == (1, 2, 3)
    assert monthly_output_quantity_for_choice(choices[0], {1: 4, 2: 6, 3: 5}) == 15
    assert choices[0].unit_weight_for_output({1: 4, 2: 6, 3: 5}) == 2.066666666666667
    assert format_monthly_input_choice(choices[0]) == "전체"

    assert choices[1].block_ids == (1, 2)
    assert monthly_output_quantity_for_choice(choices[1], {1: 4, 2: 6, 3: 5}) == 10
    assert choices[1].unit_weight_for_output({1: 4, 2: 6}) == 2.6
    assert format_monthly_input_choice(choices[1]) == "P1, P2/A (2개 투입, 10 EA, 평균 2.6 kg/EA)"


def test_monthly_total_input_choice_adds_all_raw_material_output_quantities():
    choices = build_monthly_input_choices(
        [
            ProcessBlock(
                id=1,
                type="INPUT",
                x=0,
                y=0,
                product_name="P1",
                material_name="A",
                input_quantity=10,
                unit_weight_kg_per_ea=2,
            ),
            ProcessBlock(
                id=2,
                type="INPUT",
                x=0,
                y=0,
                product_name="P2",
                material_name="B",
                input_quantity=10,
                unit_weight_kg_per_ea=3,
            ),
            ProcessBlock(
                id=3,
                type="INPUT",
                x=0,
                y=0,
                product_name="P3",
                material_name="C",
                input_quantity=10,
                unit_weight_kg_per_ea=4,
            ),
        ]
    )

    total_choice = choices[0]

    assert total_choice.is_total is True
    assert total_choice.total_input_quantity == 30
    assert monthly_output_quantity_for_choice(total_choice, {1: 10, 2: 10, 3: 10}) == 30
    assert total_choice.unit_weight_for_output({1: 10, 2: 10, 3: 10}) == 3


def test_realized_weekly_minutes_per_ea_uses_weekly_minutes_and_total_output():
    result = SimulationResult(
        timeline=[],
        total_time=10,
        total_input_quantity=10,
        final_output_quantity=10,
        input_quantity_by_product={},
        final_output_quantity_by_product={},
        final_output_quantity_by_source_block={1: 4, 2: 6},
        unique_product_count=0,
        bottleneck_id=None,
        bottleneck_throughput=0,
        process_flow=[],
    )

    assert realized_weekly_minutes_per_ea(available_minutes=8640, result=result) == 864


def test_limited_number_input_accepts_blank_and_values_within_limit():
    assert is_limited_number_input("", 24) is True
    assert is_limited_number_input("0", 24) is True
    assert is_limited_number_input("24", 24) is True
    assert is_limited_number_input("24.1", 24) is False
    assert is_limited_number_input("-1", 24) is False
    assert is_limited_number_input("abc", 24) is False


def test_block_taxonomy_uses_approved_order_and_labels():
    assert list(BLOCK_TYPES) == [
        "INPUT",
        "WORK_WAITING",
        "PREPROCESS",
        "BENDING",
        "DRAWING",
        "CUTTING",
        "HEAT",
        "CORRECTION",
        "POSTPROCESS",
        "INSPECTION",
        "PACKING",
        "HOIST",
        "FREE",
    ]
    assert [block_type.label for block_type in BLOCK_TYPES.values()] == [
        "원자재 투입",
        "작업대기",
        "전처리",
        "구부",
        "인발",
        "절단",
        "열처리",
        "교정",
        "후처리",
        "검사",
        "포장",
        "호이스트",
        "Free Block",
    ]

    old_labels = {"적재", "프레스 교정기", "자동진직도 측정기", "절단기", "열처리기"}
    assert old_labels.isdisjoint({block_type.label for block_type in BLOCK_TYPES.values()})


def test_new_process_taxonomy_defaults_do_not_change_special_blocks():
    new_normal_types = [
        "WORK_WAITING",
        "PREPROCESS",
        "BENDING",
        "DRAWING",
        "CORRECTION",
        "POSTPROCESS",
        "INSPECTION",
        "PACKING",
    ]
    for block_type in new_normal_types:
        assert BLOCK_TYPES[block_type].default_process_time_per_ea == 30.0
        assert BLOCK_TYPES[block_type].default_concurrent_capacity == 1

    assert BLOCK_TYPES["CUTTING"].default_process_time_per_ea == 45
    assert BLOCK_TYPES["HEAT"].default_process_time_per_ea == 120
    assert BLOCK_TYPES["HOIST"].default_transport_capacity == 4
    assert BLOCK_TYPES["HOIST"].default_transport_time == 3.0
    assert BLOCK_TYPES["INPUT"].default_input_quantity == 10
    assert BLOCK_TYPES["FREE"].default_process_time_per_ea == 30


def test_input_block_canvas_title_uses_compact_label():
    view = CanvasView.__new__(CanvasView)
    block = ProcessBlock(
        id=1,
        type="INPUT",
        x=0,
        y=0,
        product_name="제품",
        material_name="원자재",
    )

    assert view._block_canvas_title(block) == "제품: 제품\n원자재: 원자재"


def test_input_block_canvas_title_truncates_long_labels():
    view = CanvasView.__new__(CanvasView)
    block = ProcessBlock(
        id=1,
        type="INPUT",
        x=0,
        y=0,
        product_name="긴제품이름123",
        material_name="긴원자재이름123",
    )

    assert view._block_canvas_title(block) == "제품: 긴제품이...\n원자재: 긴원자재..."


def test_palette_list_width_is_capped_when_pane_is_stretched():
    assert PaletteView._bounded_list_width(container_width=900, scrollbar_width=17) == (
        PaletteView.LIST_MAX_WIDTH
    )
    assert PaletteView._bounded_list_width(container_width=140, scrollbar_width=17) == 119


def diagram_block(block_id: int, x: float, y: float) -> ProcessBlock:
    return ProcessBlock(id=block_id, type="CUTTING", x=x, y=y, width=150, height=80)


def test_connection_path_uses_facing_edges_when_target_is_left():
    view = CanvasView.__new__(CanvasView)
    from_block = diagram_block(1, x=320, y=100)
    to_block = diagram_block(2, x=80, y=120)

    points, _delete_position = view._connection_path(from_block, to_block)

    assert points[0] == from_block.x - CanvasView.CONNECTION_GAP
    assert points[1] == from_block.y + from_block.height / 2
    assert points[6] == to_block.x + to_block.width + CanvasView.CONNECTION_GAP
    assert points[7] == to_block.y + to_block.height / 2


def test_connection_path_uses_vertical_edges_when_target_is_below():
    view = CanvasView.__new__(CanvasView)
    from_block = diagram_block(1, x=120, y=60)
    to_block = diagram_block(2, x=145, y=260)

    points, _delete_position = view._connection_path(from_block, to_block)

    assert points[0] == from_block.x + from_block.width / 2
    assert points[1] == from_block.y + from_block.height + CanvasView.CONNECTION_GAP
    assert points[6] == to_block.x + to_block.width / 2
    assert points[7] == to_block.y - CanvasView.CONNECTION_GAP
