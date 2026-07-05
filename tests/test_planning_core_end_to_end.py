import json
from pathlib import Path

from engine.planning_core import (
    compare_scenario_reports,
    extract_recipe_candidates,
    generate_load_and_risk_report,
    import_equipment_snapshot_rows,
    import_production_plan_rows,
    import_scenario_workbook_rows,
    import_tbd_recipe_rows,
    import_work_order_operation_rows,
    match_plan_lines_to_recipes,
    render_planning_run_report_snapshot,
)


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "planning_core" / "e2e"
ENGINE_VERSION = "planning-core-e2e-v1"


def test_raw_planning_fixtures_produce_deterministic_scenario_report_snapshot():
    plan_result = import_production_plan_rows(
        _rows("production_plan_rows.json"),
        plan_batch_id="PLAN-2026-07-M",
        plan_period="2026-07",
        plan_type="MONTHLY",
    )
    work_order_result = import_work_order_operation_rows(
        _rows("work_order_rows.json"),
        import_batch_id="WO-HISTORY-2026-06",
    )
    equipment_result = import_equipment_snapshot_rows(
        _rows("equipment_rows.json"),
        snapshot_batch_id="EQ-SNAPSHOT-2026-07-01",
        snapshot_at="2026-07-01T08:00:00",
    )
    tbd_result = import_tbd_recipe_rows(
        _rows("tbd_recipe_header_rows.json"),
        _rows("tbd_recipe_step_rows.json"),
        import_batch_id="TBD-2026-07",
    )
    scenario_result = import_scenario_workbook_rows(
        header_rows=_rows("scenario_header_rows.json"),
        rule_rows=_rows("scenario_rule_rows.json"),
        equipment_override_rows=_rows("scenario_equipment_override_rows.json"),
        priority_override_rows=_rows("scenario_priority_override_rows.json"),
        recipe_override_rows=_rows("scenario_recipe_override_rows.json"),
        output_request_rows=_rows("scenario_output_request_rows.json"),
        engine_version=ENGINE_VERSION,
    )

    assert plan_result.errors == ()
    assert work_order_result.errors == ()
    assert equipment_result.errors == ()
    assert tbd_result.errors == ()
    assert scenario_result.errors == ()

    recipe_candidates = extract_recipe_candidates(work_order_result.operations)
    recipe_headers = recipe_candidates.recipe_headers + tbd_result.recipe_headers
    recipe_steps = recipe_candidates.recipe_steps + tbd_result.recipe_steps
    matching_result = match_plan_lines_to_recipes(
        plan_result.lines,
        recipe_headers,
    )

    scenario_reports = {
        scenario.scenario_id: generate_load_and_risk_report(
            plan_lines=plan_result.lines,
            matching_result=matching_result,
            recipe_steps=recipe_steps,
            equipment_snapshots=equipment_result.snapshots,
            equipment_overrides=scenario.equipment_overrides,
        )
        for scenario in scenario_result.scenario_definitions
        if scenario.is_executable
    }
    scenario_comparison = compare_scenario_reports(
        scenarios=scenario_result.scenario_definitions,
        reports_by_scenario_id=scenario_reports,
        engine_version=ENGINE_VERSION,
    )

    snapshot = render_planning_run_report_snapshot(
        matching_result=matching_result,
        scenario_reports=scenario_reports,
        scenario_comparison=scenario_comparison,
    )

    assert snapshot == render_planning_run_report_snapshot(
        matching_result=matching_result,
        scenario_reports=scenario_reports,
        scenario_comparison=scenario_comparison,
    )
    assert snapshot == (
        FIXTURE_DIR / "expected_planning_run_report_snapshot.json"
    ).read_text(encoding="utf-8")
    assert [row.scenario_id for row in scenario_comparison.rows] == [
        "SCN-BASE",
        "SCN-HYD-CUT-DOWN",
    ]
    assert scenario_comparison.skipped_scenario_ids == ("SCN-AI-DRAFT",)
    assert matching_result.matches[2].status == "MISSING"
    assert matching_result.matches[2].tbd_recipe_ids == ("TBD-SHP-300",)


def _rows(file_name: str):
    return json.loads((FIXTURE_DIR / file_name).read_text(encoding="utf-8"))
