from engine.planning_core import (
    PlanningWorkbookRunConfig,
    load_planning_workbook_rows,
    render_planning_workbook_report_snapshot,
)
from planning_workbook_test_utils import (
    ENGINE_VERSION,
    FIXTURE_DIR,
    write_e2e_planning_workbook,
)


def test_planning_workbook_report_matches_deterministic_e2e_snapshot(tmp_path):
    workbook_path = tmp_path / "planning-input.xlsx"
    write_e2e_planning_workbook(workbook_path)

    workbook_rows = load_planning_workbook_rows(workbook_path)

    assert workbook_rows.production_plan_rows[0]["item_code"] == "HYD-100"
    assert workbook_rows.scenario_equipment_override_rows[0]["is_available"] == "false"
    assert workbook_rows.scenario_recipe_override_rows == ()

    snapshot = render_planning_workbook_report_snapshot(
        workbook_path,
        config=PlanningWorkbookRunConfig(
            plan_batch_id="PLAN-2026-07-M",
            plan_period="2026-07",
            plan_type="MONTHLY",
            work_order_import_batch_id="WO-HISTORY-2026-06",
            equipment_snapshot_batch_id="EQ-SNAPSHOT-2026-07-01",
            equipment_snapshot_at="2026-07-01T08:00:00",
            tbd_import_batch_id="TBD-2026-07",
            engine_version=ENGINE_VERSION,
        ),
    )

    assert snapshot == (
        FIXTURE_DIR / "expected_planning_run_report_snapshot.json"
    ).read_text(encoding="utf-8")
