import json
from pathlib import Path

from engine.planning_core import import_production_plan_rows


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "planning_core" / "production_plan_import"


def test_monthly_production_plan_rows_import_with_totals_and_domains():
    rows = _read_fixture_rows("monthly_rows.json")

    result = import_production_plan_rows(
        rows,
        plan_batch_id="PLAN-2026-07-M",
        plan_period="2026-07",
        plan_type="MONTHLY",
    )

    assert result.errors == ()
    assert len(result.lines) == 2
    assert sum(line.order_quantity for line in result.lines) == 200
    assert sum(line.weight or 0 for line in result.lines) == 5500.5
    assert result.lines[0].domain_code == "HYDRAULIC"
    assert result.lines[0].domain_label == "유압"
    assert result.lines[0].source_row_id == "monthly-row-2"
    assert result.lines[1].domain_code == "STS"
    assert result.lines[1].domain_label == "STS"
    assert result.lines[1].source_row_id == "monthly-row-3"


def test_invalid_production_plan_row_reports_field_error_without_stopping_import():
    rows = [
        {
            "작업장": "유압",
            "고객": "세진산업",
            "고객주문참조": "전화요청-7월-A",
            "품목코드": "HYD-100",
            "품목명": "유압 실린더 A",
            "수량": "120",
        },
        {
            "작업장": "STS",
            "고객": "대한금속",
            "고객주문참조": "STS-긴급-01",
            "품목코드": "STS-200",
            "품목명": "STS 배관 B",
            "수량": "many",
        },
    ]

    result = import_production_plan_rows(
        rows,
        plan_batch_id="PLAN-2026-07-M",
        plan_period="2026-07",
        plan_type="MONTHLY",
    )

    assert len(result.lines) == 1
    assert result.lines[0].item_code == "HYD-100"
    assert len(result.errors) == 1
    assert result.errors[0].source_row_id == "row-3"
    assert result.errors[0].field == "order_quantity"
    assert "order_quantity" in result.errors[0].message
    assert result.errors[0].raw_values["수량"] == "many"


def test_weekly_plan_import_trims_headers_and_preserves_raw_source_values():
    rows = _read_fixture_rows("weekly_rows_with_spaced_headers.json")

    result = import_production_plan_rows(
        rows,
        plan_batch_id="PLAN-2026-W27",
        plan_period="2026-W27",
        plan_type="weekly",
    )

    assert result.errors == ()
    assert len(result.lines) == 1
    line = result.lines[0]
    assert line.plan_type == "WEEKLY"
    assert line.domain_code == "SHAPED_MATERIAL"
    assert line.domain_label == "이형재"
    assert line.customer_name == "한림소재"
    assert line.customer_order_ref == "카톡요청/7월 2차"
    assert line.product_group == "PROFILE"
    assert line.item_code == "SHP-300"
    assert line.item_name == "이형재 프로파일 C"
    assert line.order_quantity == 45
    assert line.weight == 980
    assert line.source_row_id == "weekly-row-5"
    assert line.raw_values[" 고객주문참조 "] == "카톡요청/7월 2차"


def _read_fixture_rows(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
