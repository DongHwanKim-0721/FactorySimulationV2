import json
from pathlib import Path

from engine.planning_core import (
    extract_recipe_candidates,
    import_work_order_operation_rows,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "planning_core" / "work_order_import"


def test_historical_work_order_rows_import_into_normalized_operations():
    rows = _read_fixture_rows("historical_rows.json")

    result = import_work_order_operation_rows(
        rows,
        import_batch_id="WO-HIST-2026-W26",
    )

    assert result.errors == ()
    assert len(result.operations) == 3

    operation = result.operations[0]
    assert operation.import_batch_id == "WO-HIST-2026-W26"
    assert operation.operation_date == "2026-06-25"
    assert operation.domain_code == "HYDRAULIC"
    assert operation.shift_or_team == "A"
    assert operation.work_order_no == "WO-HYD-001"
    assert operation.process_sequence == 10
    assert operation.process_group == "CUTTING"
    assert operation.process_name == "절단"
    assert operation.operation_sequence == 1
    assert operation.equipment_name == "유압 절단기 1"
    assert operation.item_code == "HYD-100"
    assert operation.item_name == "유압 실린더 A"
    assert operation.instruction_quantity == 120
    assert operation.input_quantity == 120
    assert operation.output_quantity == 118
    assert operation.defect_quantity == 2
    assert operation.unit == "EA"
    assert operation.first_input_material == "SCM440"
    assert operation.source_row_id == "wo-row-8"
    assert operation.raw_values["작업장"] == "유압"


def test_invalid_work_order_row_reports_field_error_without_stopping_import():
    rows = [
        {
            "작업장": "유압",
            "작업지시번호": "WO-HYD-VALID",
            "공정순서": "10",
            "공정그룹": "CUTTING",
            "공정명": "절단",
            "작업순서": "1",
            "품목코드": "HYD-100",
            "source_row_id": "wo-valid-row-2",
        },
        {
            "작업장": "STS",
            "작업지시번호": "WO-STS-BAD",
            "공정순서": "first",
            "공정그룹": "POLISHING",
            "공정명": "연마",
            "작업순서": "1",
            "품목코드": "STS-200",
            "source_row_id": "wo-bad-row-3",
        },
    ]

    result = import_work_order_operation_rows(
        rows,
        import_batch_id="WO-HIST-INVALID",
    )

    assert len(result.operations) == 1
    assert result.operations[0].work_order_no == "WO-HYD-VALID"
    assert len(result.errors) == 1
    assert result.errors[0].source_row_id == "wo-bad-row-3"
    assert result.errors[0].field == "process_sequence"
    assert "process_sequence" in result.errors[0].message
    assert result.errors[0].raw_values["공정순서"] == "first"


def test_historical_work_order_operations_extract_ordered_recipe_candidates():
    import_result = import_work_order_operation_rows(
        _read_fixture_rows("historical_rows.json"),
        import_batch_id="WO-HIST-2026-W26",
    )

    result = extract_recipe_candidates(import_result.operations)

    assert len(result.recipe_headers) == 2
    hydraulic_header = _find_header(result.recipe_headers, "HYDRAULIC", "HYD-100")
    assert hydraulic_header.recipe_id == "AUTO-HYDRAULIC-HYD-100"
    assert hydraulic_header.recipe_version == "1"
    assert hydraulic_header.recipe_status == "AUTO_CANDIDATE"
    assert hydraulic_header.item_name == "유압 실린더 A"
    assert hydraulic_header.first_input_material == "SCM440"
    assert hydraulic_header.source_type == "HISTORICAL_WO"
    assert hydraulic_header.source_import_batch_id == "WO-HIST-2026-W26"
    assert hydraulic_header.source_work_order_refs == ("WO-HYD-001",)
    assert hydraulic_header.usage_count == 1
    assert hydraulic_header.confidence == "OBSERVED_SINGLE"
    assert hydraulic_header.last_observed_date == "2026-06-25"

    hydraulic_steps = [
        step
        for step in result.recipe_steps
        if step.recipe_id == hydraulic_header.recipe_id
    ]
    assert [step.step_no for step in hydraulic_steps] == [10, 20]
    assert [step.process_group for step in hydraulic_steps] == ["CUTTING", "MACHINING"]
    assert [step.process_name for step in hydraulic_steps] == ["절단", "가공"]
    assert [step.preferred_equipment for step in hydraulic_steps] == [
        "유압 절단기 1",
        "유압 가공기 1",
    ]
    assert [step.source_row_id for step in hydraulic_steps] == ["wo-row-8", "wo-row-9"]
    assert all(step.input_basis == "EA" for step in hydraulic_steps)


def test_recipe_candidates_do_not_group_same_item_across_domains():
    rows = [
        {
            "작업장": "유압",
            "작업지시번호": "WO-HYD-COMMON",
            "공정순서": "10",
            "공정그룹": "CUTTING",
            "공정명": "절단",
            "작업순서": "1",
            "설비명": "유압 절단기 1",
            "품목코드": "COMMON-1",
            "품목명": "공통 품목",
            "단위": "EA",
            "source_row_id": "wo-common-row-2",
        },
        {
            "작업장": "STS",
            "작업지시번호": "WO-STS-COMMON",
            "공정순서": "10",
            "공정그룹": "POLISHING",
            "공정명": "연마",
            "작업순서": "1",
            "설비명": "STS 연마기 1",
            "품목코드": "COMMON-1",
            "품목명": "공통 품목",
            "단위": "EA",
            "source_row_id": "wo-common-row-3",
        },
    ]
    import_result = import_work_order_operation_rows(
        rows,
        import_batch_id="WO-HIST-COMMON",
    )

    result = extract_recipe_candidates(import_result.operations)

    assert import_result.errors == ()
    assert {
        (header.domain_code, header.item_code, header.source_work_order_refs)
        for header in result.recipe_headers
    } == {
        ("HYDRAULIC", "COMMON-1", ("WO-HYD-COMMON",)),
        ("STS", "COMMON-1", ("WO-STS-COMMON",)),
    }
    assert {
        (step.domain_code, step.recipe_id, step.process_group)
        for step in result.recipe_steps
    } == {
        ("HYDRAULIC", "AUTO-HYDRAULIC-COMMON-1", "CUTTING"),
        ("STS", "AUTO-STS-COMMON-1", "POLISHING"),
    }


def _read_fixture_rows(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))


def _find_header(headers, domain_code, item_code):
    for header in headers:
        if header.domain_code == domain_code and header.item_code == item_code:
            return header
    raise AssertionError(f"missing recipe header for {domain_code}/{item_code}")
