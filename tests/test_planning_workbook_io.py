import json

from engine.planning_core import (
    PLANNING_WORKBOOK_SHEETS,
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


def test_planning_workbook_scenario_reports_apply_domain_filters_and_recipe_overrides(
    tmp_path,
):
    workbook_path = tmp_path / "planning-input.xlsx"
    scenario_header_rows = _fixture_rows("scenario_header_rows.json")
    scenario_header_rows[0]["domain_filters"] = "HYDRAULIC"
    scenario_header_rows[1]["domain_filters"] = "SHAPED_MATERIAL"
    recipe_override_rows = [
        {
            "source_row_id": "recipe-override-row-2",
            "scenario_id": "SCN-HYD-CUT-DOWN",
            "domain": "SHAPED_MATERIAL",
            "item_code": "SHP-300",
            "recipe_id": "TBD-SHP-300",
        }
    ]
    write_e2e_planning_workbook(
        workbook_path,
        sheet_rows_by_name={
            PLANNING_WORKBOOK_SHEETS["scenario_header_rows"]: scenario_header_rows,
            PLANNING_WORKBOOK_SHEETS[
                "scenario_recipe_override_rows"
            ]: recipe_override_rows,
        },
    )

    snapshot = render_planning_workbook_report_snapshot(
        workbook_path,
        config=_config(),
    )
    report = json.loads(snapshot)

    assert report["recipe_matching"]["match_status_counts"]["MISSING"] == 1

    hydraulic_report = report["scenario_reports"]["SCN-BASE"]
    assert hydraulic_report["missing_recipe_count"] == 0
    assert {
        row["domain_code"]
        for row in hydraulic_report["load_summary_rows"]
    } == {"HYDRAULIC"}

    shaped_report = report["scenario_reports"]["SCN-HYD-CUT-DOWN"]
    assert shaped_report["missing_recipe_count"] == 0
    assert shaped_report["unplannable_line_count"] == 0
    assert {
        row["recipe_id"]
        for row in shaped_report["load_summary_rows"]
    } == {"TBD-SHP-300"}
    assert {
        row["domain_code"]
        for row in shaped_report["load_summary_rows"]
    } == {"SHAPED_MATERIAL"}


def _config():
    return PlanningWorkbookRunConfig(
        plan_batch_id="PLAN-2026-07-M",
        plan_period="2026-07",
        plan_type="MONTHLY",
        work_order_import_batch_id="WO-HISTORY-2026-06",
        equipment_snapshot_batch_id="EQ-SNAPSHOT-2026-07-01",
        equipment_snapshot_at="2026-07-01T08:00:00",
        tbd_import_batch_id="TBD-2026-07",
        engine_version=ENGINE_VERSION,
    )


def _fixture_rows(file_name):
    return json.loads((FIXTURE_DIR / file_name).read_text(encoding="utf-8"))
