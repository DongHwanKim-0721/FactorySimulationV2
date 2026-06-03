import pytest

from engine.models import Operator, OperatorAssignment, ProcessBlock, ProcessConnection
from engine.simulation import simulate, topological_flow


def input_block(
    block_id: int,
    product_name: str = "P",
    material_name: str = "A",
    quantity: int = 10,
    input_time: float = 0,
) -> ProcessBlock:
    return ProcessBlock(
        id=block_id,
        type="INPUT",
        x=0,
        y=0,
        product_name=product_name,
        material_name=material_name,
        input_quantity=quantity,
        input_time=input_time,
    )


def process_block(
    block_id: int,
    process_time: float = 1,
    concurrent_capacity: int = 1,
    block_type: str = "CUTTING",
) -> ProcessBlock:
    return ProcessBlock(
        id=block_id,
        type=block_type,
        x=0,
        y=0,
        process_time_per_ea=process_time,
        concurrent_capacity=concurrent_capacity,
    )


def hoist_block(
    block_id: int,
    transport_capacity: int = 4,
    transport_time: float = 3,
) -> ProcessBlock:
    return ProcessBlock(
        id=block_id,
        type="HOIST",
        x=0,
        y=0,
        transport_capacity=transport_capacity,
        transport_time=transport_time,
    )


def processed_by_id(result):
    return {item.block_id: item.total_processed for item in result.timeline}


def bundles_for(result, block_id: int):
    return next(item.bundles for item in result.timeline if item.block_id == block_id)


def starts_for(result, block_id: int):
    return next(item.start_times for item in result.timeline if item.block_id == block_id)


def waits_for(result, block_id: int):
    return next(item.waiting_times for item in result.timeline if item.block_id == block_id)


def test_input_only_block_generates_one_bundle_and_preserves_quantity():
    result = simulate([input_block(1, material_name="A", quantity=10, input_time=5)], [])

    assert result.total_time == 5
    assert result.total_input_quantity == 10
    assert result.final_output_quantity == 10
    assert result.bottleneck_id is None
    assert processed_by_id(result) == {1: 10}
    assert result.timeline[0].processed_bundle_count == 1
    assert result.timeline[0].bundles[0].product_name == "P"
    assert result.timeline[0].bundles[0].material_name == "A"


def test_multiple_input_only_blocks_sum_input_and_output_quantities():
    blocks = [
        input_block(1, material_name="A", quantity=10, input_time=2),
        input_block(2, material_name="B", quantity=5, input_time=7),
    ]

    result = simulate(blocks, [])

    assert result.total_time == 7
    assert result.total_input_quantity == 15
    assert result.final_output_quantity == 15
    assert processed_by_id(result) == {1: 10, 2: 5}


def test_linear_process_flow_uses_bundle_cumulative_time():
    blocks = [
        input_block(1, quantity=10, input_time=0),
        process_block(2, process_time=1, concurrent_capacity=1),
        process_block(3, process_time=1, concurrent_capacity=1),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=2),
        ProcessConnection(id=2, from_block=2, to_block=3),
    ]

    result = simulate(blocks, connections)

    assert result.total_time == 20
    assert result.final_output_quantity == 10
    assert processed_by_id(result) == {1: 10, 2: 10, 3: 10}
    assert [item.processed_bundle_count for item in result.timeline] == [1, 1, 1]


def test_input_time_is_fixed_time_for_the_whole_bundle():
    blocks = [
        input_block(1, quantity=10, input_time=5),
        process_block(2, process_time=1, concurrent_capacity=1),
        process_block(3, process_time=1, concurrent_capacity=1),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=2),
        ProcessConnection(id=2, from_block=2, to_block=3),
    ]

    result = simulate(blocks, connections)

    assert result.total_time == 25


def test_hoist_uses_transport_capacity_and_reports_trip_count():
    blocks = [
        input_block(1, quantity=10),
        hoist_block(2, transport_capacity=4, transport_time=3),
    ]
    connections = [ProcessConnection(id=1, from_block=1, to_block=2)]

    result = simulate(blocks, connections)
    hoist = next(item for item in result.timeline if item.block_id == 2)

    assert result.total_time == 9
    assert hoist.total_processed == 10
    assert hoist.processed_bundle_count == 1
    assert hoist.transport_trips == 3
    assert hoist.bundles[0].transport_trips == 3


def test_engine_rejects_invalid_bundle_graph_connections():
    blocks = [input_block(1), process_block(2), input_block(3)]

    with pytest.raises(ValueError, match="원자재 투입 블록"):
        simulate(blocks[:2], [ProcessConnection(id=1, from_block=2, to_block=1)])

    with pytest.raises(ValueError, match="입력 연결 없이"):
        simulate(blocks[:2], [])

    with pytest.raises(ValueError, match="원자재 투입 블록"):
        simulate(blocks, [ProcessConnection(id=1, from_block=1, to_block=3)])


def test_engine_rejects_invalid_numeric_fields():
    with pytest.raises(ValueError, match="제품명"):
        simulate([input_block(1, product_name=" ")], [])

    with pytest.raises(ValueError, match="투입 원자재 수"):
        simulate([input_block(1, quantity=-1)], [])

    with pytest.raises(ValueError, match="투입 시간"):
        simulate([input_block(1, input_time=-1)], [])

    with pytest.raises(ValueError, match="동시 가공 수량"):
        simulate(
            [input_block(1), process_block(2, concurrent_capacity=0)],
            [ProcessConnection(id=1, from_block=1, to_block=2)],
        )

    with pytest.raises(ValueError, match="1회 운반 수량"):
        simulate(
            [input_block(1), hoist_block(2, transport_capacity=0)],
            [ProcessConnection(id=1, from_block=1, to_block=2)],
        )


def test_stable_topological_flow_preserves_block_order_for_ready_blocks():
    blocks = [
        input_block(1),
        input_block(3, material_name="B"),
        process_block(2),
    ]
    connections = [ProcessConnection(id=1, from_block=1, to_block=2)]

    assert topological_flow(blocks, connections) == [1, 3, 2]


def test_branch_routing_uses_child_capabilities_without_copying_ea():
    blocks = [
        input_block(1, quantity=10),
        process_block(2, concurrent_capacity=4),
        hoist_block(3, transport_capacity=1, transport_time=1),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=2),
        ProcessConnection(id=2, from_block=1, to_block=3),
    ]

    result = simulate(blocks, connections)

    assert processed_by_id(result) == {1: 10, 2: 8, 3: 2}
    assert result.total_input_quantity == 10
    assert result.final_output_quantity == 10
    assert [bundle.quantity for bundle in bundles_for(result, 2)] == [8]
    assert [bundle.quantity for bundle in bundles_for(result, 3)] == [2]


def test_branch_after_hoist_uses_same_weighted_split_rule():
    blocks = [
        input_block(1, quantity=10),
        hoist_block(2, transport_capacity=10, transport_time=1),
        process_block(3, concurrent_capacity=4),
        hoist_block(4, transport_capacity=1, transport_time=1),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=2),
        ProcessConnection(id=2, from_block=2, to_block=3),
        ProcessConnection(id=3, from_block=2, to_block=4),
    ]

    result = simulate(blocks, connections)

    assert processed_by_id(result) == {1: 10, 2: 10, 3: 8, 4: 2}
    assert result.final_output_quantity == 10


def test_join_uses_bundle_fifo_and_does_not_merge_bundles():
    blocks = [
        input_block(1, material_name="A", quantity=5, input_time=0),
        input_block(2, material_name="B", quantity=5, input_time=2),
        process_block(3, process_time=1, concurrent_capacity=5),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=3),
        ProcessConnection(id=2, from_block=2, to_block=3),
    ]

    result = simulate(blocks, connections)
    joined_bundles = bundles_for(result, 3)

    assert result.total_input_quantity == 10
    assert result.final_output_quantity == 10
    assert [(bundle.material_name, bundle.quantity) for bundle in joined_bundles] == [
        ("A", 5),
        ("B", 5),
    ]
    assert [bundle.start_time for bundle in joined_bundles] == [0, 2]


def test_process_blocks_group_same_material_before_switching_materials():
    blocks = [
        input_block(1, material_name="A", quantity=5, input_time=0),
        input_block(2, material_name="B", quantity=5, input_time=0),
        input_block(3, material_name="A", quantity=5, input_time=2),
        process_block(4, process_time=1, concurrent_capacity=5),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=4),
        ProcessConnection(id=2, from_block=2, to_block=4),
        ProcessConnection(id=3, from_block=3, to_block=4),
    ]

    result = simulate(blocks, connections)
    processed = bundles_for(result, 4)

    assert [(bundle.material_name, bundle.start_time) for bundle in processed] == [
        ("A", 0),
        ("A", 2),
        ("B", 3),
    ]


def test_hoist_blocks_keep_fifo_instead_of_material_grouping():
    blocks = [
        input_block(1, material_name="A", quantity=5, input_time=0),
        input_block(2, material_name="B", quantity=5, input_time=0),
        input_block(3, material_name="A", quantity=5, input_time=2),
        hoist_block(4, transport_capacity=5, transport_time=1),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=4),
        ProcessConnection(id=2, from_block=2, to_block=4),
        ProcessConnection(id=3, from_block=3, to_block=4),
    ]

    result = simulate(blocks, connections)
    processed = bundles_for(result, 4)

    assert [(bundle.material_name, bundle.start_time) for bundle in processed] == [
        ("A", 0),
        ("B", 1),
        ("A", 2),
    ]


def test_product_label_is_preserved_through_branch_and_join():
    blocks = [
        input_block(1, product_name="P1", material_name="A", quantity=10),
        process_block(2, concurrent_capacity=4),
        hoist_block(3, transport_capacity=1, transport_time=1),
        process_block(4, concurrent_capacity=10),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=2),
        ProcessConnection(id=2, from_block=1, to_block=3),
        ProcessConnection(id=3, from_block=2, to_block=4),
        ProcessConnection(id=4, from_block=3, to_block=4),
    ]

    result = simulate(blocks, connections)

    branch_one = bundles_for(result, 2)
    branch_two = bundles_for(result, 3)
    joined = bundles_for(result, 4)

    assert [(bundle.product_name, bundle.material_name) for bundle in branch_one] == [
        ("P1", "A")
    ]
    assert [(bundle.product_name, bundle.material_name) for bundle in branch_two] == [
        ("P1", "A")
    ]
    assert [(bundle.product_name, bundle.material_name) for bundle in joined] == [
        ("P1", "A"),
        ("P1", "A"),
    ]
    assert len({bundle.bundle_id for bundle in joined}) == 2


def test_same_product_and_material_inputs_are_not_merged():
    blocks = [
        input_block(1, product_name="P1", material_name="A", quantity=5),
        input_block(2, product_name="P1", material_name="A", quantity=7),
        process_block(3, process_time=1, concurrent_capacity=10),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=3),
        ProcessConnection(id=2, from_block=2, to_block=3),
    ]

    result = simulate(blocks, connections)
    joined = bundles_for(result, 3)

    assert [
        (bundle.product_name, bundle.material_name, bundle.quantity)
        for bundle in joined
    ] == [
        ("P1", "A", 5),
        ("P1", "A", 7),
    ]
    assert len({bundle.bundle_id for bundle in joined}) == 2


def test_product_quantities_are_aggregated_for_inputs_and_sink_outputs():
    blocks = [
        input_block(1, product_name="P1", material_name="A", quantity=4),
        input_block(2, product_name="P1", material_name="B", quantity=6),
        input_block(3, product_name="P2", material_name="C", quantity=3),
        process_block(4, process_time=1, concurrent_capacity=10),
        hoist_block(5, transport_capacity=10, transport_time=1),
        process_block(6, process_time=1, concurrent_capacity=10),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=4),
        ProcessConnection(id=2, from_block=2, to_block=5),
        ProcessConnection(id=3, from_block=3, to_block=6),
    ]

    result = simulate(blocks, connections)

    assert result.unique_product_count == 2
    assert result.input_quantity_by_product == {"P1": 10, "P2": 3}
    assert result.final_output_quantity_by_product == {"P1": 10, "P2": 3}


def test_product_label_does_not_affect_material_grouping():
    blocks = [
        input_block(1, product_name="P1", material_name="A", quantity=5, input_time=0),
        input_block(2, product_name="P3", material_name="B", quantity=5, input_time=0),
        input_block(3, product_name="P2", material_name="A", quantity=5, input_time=2),
        process_block(4, process_time=1, concurrent_capacity=5),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=4),
        ProcessConnection(id=2, from_block=2, to_block=4),
        ProcessConnection(id=3, from_block=3, to_block=4),
    ]

    result = simulate(blocks, connections)
    processed = bundles_for(result, 4)

    assert [
        (bundle.product_name, bundle.material_name, bundle.start_time)
        for bundle in processed
    ] == [
        ("P1", "A", 0),
        ("P2", "A", 2),
        ("P3", "B", 3),
    ]


def test_unconnected_operators_do_not_change_simulation_results():
    blocks = [
        input_block(1, quantity=10),
        process_block(2, process_time=1, concurrent_capacity=1),
        hoist_block(3, transport_capacity=4, transport_time=3),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=2),
        ProcessConnection(id=2, from_block=2, to_block=3),
    ]
    operator = Operator(
        id=1,
        name="Operator A",
        x=0,
        y=0,
        qualified_process_types={"CUTTING"},
    )

    baseline = simulate(blocks, connections)
    with_unconnected_operator = simulate(blocks, connections, [operator], [])

    assert with_unconnected_operator.total_time == baseline.total_time
    assert [
        item.start_times for item in with_unconnected_operator.timeline
    ] == [item.start_times for item in baseline.timeline]
    assert [
        item.completion_times for item in with_unconnected_operator.timeline
    ] == [item.completion_times for item in baseline.timeline]


def test_shared_operator_delays_independent_ready_processes():
    blocks = [
        input_block(1, quantity=1),
        input_block(2, quantity=1, material_name="B"),
        process_block(3, process_time=10, concurrent_capacity=1),
        process_block(4, process_time=10, concurrent_capacity=1),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=3),
        ProcessConnection(id=2, from_block=2, to_block=4),
    ]
    operator = Operator(
        id=1,
        name="Operator A",
        x=0,
        y=0,
        qualified_process_types={"CUTTING"},
    )
    assignments = [
        OperatorAssignment(id=1, operator_id=1, block_id=3),
        OperatorAssignment(id=2, operator_id=1, block_id=4),
    ]

    result = simulate(blocks, connections, [operator], assignments)

    assert starts_for(result, 3) == [0.0]
    assert starts_for(result, 4) == [10.0]
    assert waits_for(result, 4) == [10.0]
    assert result.total_time == 20


def test_operator_assignment_preserves_linear_hoist_flow_order():
    blocks = [
        input_block(1, quantity=10),
        process_block(2, process_time=1, concurrent_capacity=10, block_type="DRAWING"),
        hoist_block(3, transport_capacity=10, transport_time=5),
        process_block(4, process_time=1, concurrent_capacity=10, block_type="POSTPROCESS"),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=2),
        ProcessConnection(id=2, from_block=2, to_block=3),
        ProcessConnection(id=3, from_block=3, to_block=4),
    ]
    operator = Operator(
        id=1,
        name="Operator A",
        x=0,
        y=0,
        qualified_process_types={"DRAWING", "POSTPROCESS"},
    )
    assignments = [
        OperatorAssignment(id=1, operator_id=1, block_id=2),
        OperatorAssignment(id=2, operator_id=1, block_id=4),
    ]

    result = simulate(blocks, connections, [operator], assignments)

    assert starts_for(result, 2) == [0.0]
    assert starts_for(result, 3) == [1.0]
    assert starts_for(result, 4) == [6.0]
    assert result.total_time == 7


def test_shared_operator_uses_earliest_ready_before_flow_order():
    blocks = [
        input_block(1, quantity=1, input_time=5),
        input_block(2, quantity=1, material_name="B", input_time=0),
        process_block(3, process_time=10, concurrent_capacity=1),
        process_block(4, process_time=10, concurrent_capacity=1),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=3),
        ProcessConnection(id=2, from_block=2, to_block=4),
    ]
    operator = Operator(
        id=1,
        name="Operator A",
        x=0,
        y=0,
        qualified_process_types={"CUTTING"},
    )
    assignments = [
        OperatorAssignment(id=1, operator_id=1, block_id=3),
        OperatorAssignment(id=2, operator_id=1, block_id=4),
    ]

    result = simulate(blocks, connections, [operator], assignments)

    assert starts_for(result, 4) == [0.0]
    assert starts_for(result, 3) == [10.0]


def test_shared_operator_clears_current_waiting_bundles_without_future_prediction():
    blocks = [
        input_block(1, material_name="A", quantity=1, input_time=0),
        input_block(2, material_name="A", quantity=1, input_time=100),
        input_block(3, material_name="B", quantity=1, input_time=10),
        process_block(4, process_time=1, concurrent_capacity=1),
        process_block(5, process_time=1, concurrent_capacity=1),
    ]
    connections = [
        ProcessConnection(id=1, from_block=1, to_block=4),
        ProcessConnection(id=2, from_block=2, to_block=4),
        ProcessConnection(id=3, from_block=3, to_block=5),
    ]
    operator = Operator(
        id=1,
        name="Operator A",
        x=0,
        y=0,
        qualified_process_types={"CUTTING"},
    )
    assignments = [
        OperatorAssignment(id=1, operator_id=1, block_id=4),
        OperatorAssignment(id=2, operator_id=1, block_id=5),
    ]

    result = simulate(blocks, connections, [operator], assignments)

    assert starts_for(result, 4) == [0.0, 100.0]
    assert starts_for(result, 5) == [10.0]
