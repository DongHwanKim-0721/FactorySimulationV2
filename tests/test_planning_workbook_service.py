import pytest

from engine.planning_core import (
    PLANNING_WORKBOOK_SHEETS,
    REPORT_WORKBOOK_SHEETS,
    PlanningWorkbookRunConfig,
    PlanningWorkbookRunRequest,
    PlanningWorkbookRunRequestError,
    create_planning_workbook_template,
    load_planning_workbook_rows,
    load_xlsx_sheet_rows,
    run_planning_workbook,
)
from engine.planning_core.cli import main
from planning_workbook_test_utils import (
    ENGINE_VERSION,
    FIXTURE_DIR,
    write_e2e_planning_workbook,
)


def test_service_run_workbook_matches_cli_and_writes_selected_reports(tmp_path, capsys):
    workbook_path = tmp_path / "planning-input.xlsx"
    cli_report_path = tmp_path / "cli-planning-run-report.json"
    service_json_path = tmp_path / "service-planning-run-report.json"
    service_report_path = tmp_path / "service-planning-run-report.xlsx"
    write_e2e_planning_workbook(workbook_path)

    cli_exit_code = main(_run_workbook_args(workbook_path, cli_report_path))
    captured = capsys.readouterr()

    result = run_planning_workbook(
        PlanningWorkbookRunRequest(
            input_workbook_path=workbook_path,
            config=_config(),
            json_output_path=service_json_path,
            report_workbook_output_path=service_report_path,
        )
    )

    expected_snapshot = (
        FIXTURE_DIR / "expected_planning_run_report_snapshot.json"
    ).read_text(encoding="utf-8")
    report_rows = load_xlsx_sheet_rows(service_report_path)

    assert cli_exit_code == 0
    assert captured.err == ""
    assert captured.out == ""
    assert result.input_workbook_path == workbook_path
    assert result.json_output_path == service_json_path
    assert result.report_workbook_output_path == service_report_path
    assert result.report_snapshot_json == expected_snapshot
    assert service_json_path.read_text(encoding="utf-8") == cli_report_path.read_text(
        encoding="utf-8"
    )
    assert service_json_path.read_text(encoding="utf-8") == expected_snapshot
    assert set(report_rows) == set(REPORT_WORKBOOK_SHEETS.values())

    summary = result.summary
    assert summary.calculation_authority == "DETERMINISTIC_ENGINE"
    assert summary.deferred_capabilities == (
        "DUE_DATE_SCHEDULING",
        "STANDARD_TIME_CALCULATION",
    )
    assert summary.total_plan_line_count == 3
    assert summary.matched_count == 2
    assert summary.missing_count == 1
    assert summary.ambiguous_count == 0
    assert summary.tbd_report_row_count == 1
    assert summary.skipped_scenario_ids == ("SCN-AI-DRAFT",)
    assert [scenario.scenario_id for scenario in summary.ranked_scenarios] == [
        "SCN-BASE",
        "SCN-HYD-CUT-DOWN",
    ]
    assert summary.ranked_scenarios[0].deterministic_score == 11400.0
    assert summary.top_bottleneck_risks[0].scenario_id == "SCN-HYD-CUT-DOWN"
    assert summary.top_bottleneck_risks[0].risk_score == 240.0


def test_service_create_template_supports_sample_and_blank_workbooks(tmp_path):
    sample_path = tmp_path / "planning-input-template.xlsx"
    blank_path = tmp_path / "blank-planning-input-template.xlsx"

    sample = create_planning_workbook_template(sample_path)
    blank = create_planning_workbook_template(blank_path, blank=True)

    sample_rows = load_planning_workbook_rows(sample_path)
    blank_rows = load_xlsx_sheet_rows(blank_path)

    assert sample.workbook_path == sample_path
    assert sample.include_examples is True
    assert blank.workbook_path == blank_path
    assert blank.include_examples is False
    assert set(blank_rows) == set(PLANNING_WORKBOOK_SHEETS.values())
    assert sample_rows.production_plan_rows[0]["item_code"] == "HYD-100"
    assert all(rows == () for rows in blank_rows.values())


def test_service_requires_explicit_run_metadata_and_output_path(tmp_path):
    workbook_path = tmp_path / "planning-input.xlsx"

    with pytest.raises(PlanningWorkbookRunRequestError) as exc_info:
        run_planning_workbook(
            PlanningWorkbookRunRequest(
                input_workbook_path=workbook_path,
                config=PlanningWorkbookRunConfig(
                    plan_batch_id="",
                    plan_period="2026-07",
                    plan_type="MONTHLY",
                    work_order_import_batch_id="WO-HISTORY-2026-06",
                    equipment_snapshot_batch_id="EQ-SNAPSHOT-2026-07-01",
                    equipment_snapshot_at="2026-07-01T08:00:00",
                    tbd_import_batch_id="TBD-2026-07",
                    engine_version=" ",
                ),
            )
        )

    message = str(exc_info.value)
    assert "plan_batch_id" in message
    assert "engine_version" in message
    assert "at least one report output path is required" in message


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


def _run_workbook_args(workbook_path, report_path):
    return [
        "run-workbook",
        str(workbook_path),
        "--out",
        str(report_path),
        "--plan-batch-id",
        "PLAN-2026-07-M",
        "--plan-period",
        "2026-07",
        "--plan-type",
        "MONTHLY",
        "--work-order-import-batch-id",
        "WO-HISTORY-2026-06",
        "--equipment-snapshot-batch-id",
        "EQ-SNAPSHOT-2026-07-01",
        "--equipment-snapshot-at",
        "2026-07-01T08:00:00",
        "--tbd-import-batch-id",
        "TBD-2026-07",
        "--engine-version",
        ENGINE_VERSION,
    ]
