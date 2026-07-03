import json
from pathlib import Path

from engine.planning_core import import_equipment_snapshot_rows


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "planning_core" / "equipment_snapshot_import"


def test_equipment_snapshot_rows_import_with_current_state_and_availability():
    rows = _read_fixture_rows("equipment_rows.json")

    result = import_equipment_snapshot_rows(
        rows,
        snapshot_batch_id="EQ-2026-07-01",
        snapshot_at="2026-07-01T08:00:00",
    )

    assert result.errors == ()
    assert len(result.snapshots) == 2

    running = result.snapshots[0]
    assert running.snapshot_batch_id == "EQ-2026-07-01"
    assert running.snapshot_at == "2026-07-01T08:00:00"
    assert running.domain_code == "HYDRAULIC"
    assert running.process_group == "CUTTING"
    assert running.equipment_id == "HYD-CUT-01"
    assert running.equipment_name == "유압 절단기 1"
    assert running.equipment_status == "가동"
    assert running.is_available is True
    assert running.unavailable_reason == ""
    assert running.current_work_order_no == "WO-HYD-001"
    assert running.current_process_sequence == "10"
    assert running.current_process_name == "절단"
    assert running.current_item_code == "HYD-100"
    assert running.current_item_name == "유압 실린더 A"
    assert running.elapsed_or_remaining_time == "02:10 elapsed"
    assert running.source_row_id == "eq-row-4"
    assert running.raw_values["상태"] == "가동"

    stopped = result.snapshots[1]
    assert stopped.domain_code == "STS"
    assert stopped.equipment_id == "STS-POL-01"
    assert stopped.equipment_name == "STS 연마기 1"
    assert stopped.equipment_status == "정비"
    assert stopped.is_available is False
    assert stopped.unavailable_reason == "정기 정비"
    assert stopped.current_work_order_no == ""
    assert stopped.raw_values["상태"] == "정비"


def test_invalid_equipment_snapshot_row_reports_error_without_stopping_import():
    rows = [
        {
            "작업장": "유압",
            "공정그룹": "CUTTING",
            "설비ID": "HYD-CUT-01",
            "설비명": "유압 절단기 1",
            "상태": "가동",
            "source_row_id": "eq-valid-row-2",
        },
        {
            "작업장": "STS",
            "공정그룹": "POLISHING",
            "설비ID": "STS-POL-01",
            "설비명": "STS 연마기 1",
            "상태": "애매함",
            "source_row_id": "eq-bad-row-3",
        },
    ]

    result = import_equipment_snapshot_rows(
        rows,
        snapshot_batch_id="EQ-2026-07-01",
        snapshot_at="2026-07-01T08:00:00",
    )

    assert len(result.snapshots) == 1
    assert result.snapshots[0].equipment_id == "HYD-CUT-01"
    assert len(result.errors) == 1
    assert result.errors[0].source_row_id == "eq-bad-row-3"
    assert result.errors[0].field == "equipment_status"
    assert "애매함" in result.errors[0].message
    assert result.errors[0].raw_values["상태"] == "애매함"


def test_equipment_snapshots_remain_scoped_to_their_planning_domain():
    rows = [
        {
            "작업장": "유압",
            "공정그룹": "CUTTING",
            "설비ID": "COMMON-EQ",
            "설비명": "공통 절단기",
            "상태": "가동",
            "source_row_id": "eq-common-row-2",
        },
        {
            "작업장": "STS",
            "공정그룹": "CUTTING",
            "설비ID": "COMMON-EQ",
            "설비명": "공통 절단기",
            "상태": "가동",
            "source_row_id": "eq-common-row-3",
        },
    ]

    result = import_equipment_snapshot_rows(
        rows,
        snapshot_batch_id="EQ-COMMON",
        snapshot_at="2026-07-01T08:00:00",
    )

    assert result.errors == ()
    assert {
        (snapshot.domain_code, snapshot.equipment_id, snapshot.source_row_id)
        for snapshot in result.snapshots
    } == {
        ("HYDRAULIC", "COMMON-EQ", "eq-common-row-2"),
        ("STS", "COMMON-EQ", "eq-common-row-3"),
    }


def _read_fixture_rows(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
