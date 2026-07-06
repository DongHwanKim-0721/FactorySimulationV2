from pathlib import Path

from app import PLANNING_LAUNCHER_BUTTON_LABEL
from engine.planning_core import (
    PlanningWorkbookBottleneckRiskSummary,
    PlanningWorkbookRunResult,
    PlanningWorkbookRunSummary,
    PlanningWorkbookScenarioSummary,
    write_planning_run_report_xlsx,
)
from planning_launcher import (
    PlanningLauncherInputs,
    build_run_request,
    format_run_readiness_inspection,
    format_output_artifacts,
    format_workbook_contract_inspection,
    format_workbook_contract_reference,
    format_run_summary,
    format_summary_lines,
    inspect_run_readiness,
    inspect_workbook_contract,
    output_artifact_paths,
    suggest_output_paths,
)
from planning_workbook_test_utils import (
    FIXTURE_DIR,
    write_e2e_planning_workbook,
)


def test_app_exposes_planning_launcher_button_label():
    assert PLANNING_LAUNCHER_BUTTON_LABEL == "Planning workbook"


def test_build_run_request_maps_ui_fields_to_service_request():
    inputs = PlanningLauncherInputs(
        input_workbook_path="planning-input.xlsx",
        json_output_path="planning-report.json",
        report_workbook_output_path=" ",
        plan_batch_id="PLAN-2026-07-M",
        plan_period="2026-07",
        plan_type="MONTHLY",
        work_order_import_batch_id="WO-HISTORY-2026-06",
        equipment_snapshot_batch_id="EQ-SNAPSHOT-2026-07-01",
        equipment_snapshot_at="2026-07-01T08:00:00",
        tbd_import_batch_id="TBD-2026-07",
        engine_version="planning-core-ui-v1",
    )

    request = build_run_request(inputs)

    assert request.input_workbook_path == "planning-input.xlsx"
    assert request.json_output_path == "planning-report.json"
    assert request.report_workbook_output_path is None
    assert request.config.plan_batch_id == "PLAN-2026-07-M"
    assert request.config.plan_period == "2026-07"
    assert request.config.plan_type == "MONTHLY"
    assert request.config.engine_version == "planning-core-ui-v1"


def test_inspect_run_readiness_accepts_complete_required_fields():
    inspection = inspect_run_readiness(_complete_inputs())
    text = format_run_readiness_inspection(inspection)

    assert inspection.is_valid is True
    assert inspection.missing_input_workbook is False
    assert inspection.missing_output_path is False
    assert inspection.missing_metadata_fields == ()
    assert "Run preflight passed" in text


def test_suggest_output_paths_uses_input_workbook_stem():
    suggested = suggest_output_paths(Path("inputs") / "planning-input.xlsx")

    assert suggested.json_output_path == (
        Path("inputs") / "planning-input-planning-run-report.json"
    )
    assert suggested.report_workbook_output_path == (
        Path("inputs") / "planning-input-planning-run-report.xlsx"
    )


def test_format_output_artifacts_lists_generated_report_paths():
    paths = (
        Path("planning-report.json"),
        Path("planning-report.xlsx"),
    )

    text = format_output_artifacts(paths)

    assert "Generated output artifacts:" in text
    assert "planning-report.json" in text
    assert "planning-report.xlsx" in text


def test_output_artifact_paths_keeps_selected_result_paths():
    result = PlanningWorkbookRunResult(
        input_workbook_path=Path("planning-input.xlsx"),
        json_output_path=Path("planning-report.json"),
        report_workbook_output_path=None,
        report_snapshot_json="{}",
        summary=_summary(),
    )

    assert output_artifact_paths(result) == (Path("planning-report.json"),)


def test_format_output_artifacts_handles_empty_session():
    assert format_output_artifacts(()) == (
        "No output artifacts have been generated in this session."
    )


def test_inspect_run_readiness_lists_missing_metadata_before_execution():
    inputs = PlanningLauncherInputs(
        input_workbook_path=" ",
        json_output_path=" ",
        report_workbook_output_path=" ",
        plan_batch_id="",
        plan_period="2026-07",
        plan_type="",
        work_order_import_batch_id="WO-HISTORY-2026-06",
        equipment_snapshot_batch_id="",
        equipment_snapshot_at="2026-07-01T08:00:00",
        tbd_import_batch_id="TBD-2026-07",
        engine_version="planning-core-ui-v1",
    )

    inspection = inspect_run_readiness(inputs)
    text = format_run_readiness_inspection(inspection)

    assert inspection.is_valid is False
    assert inspection.missing_input_workbook is True
    assert inspection.missing_output_path is True
    assert inspection.missing_metadata_fields == (
        "Plan batch id",
        "Plan type",
        "Equipment snapshot batch id",
    )
    assert "Run preflight failed" in text
    assert "Input workbook" in text
    assert "JSON report or report workbook output path" in text
    assert "Plan batch id" in text
    assert "Equipment snapshot batch id" in text


def test_format_workbook_contract_reference_points_to_contract_doc():
    text = format_workbook_contract_reference()

    assert "Workbook contract document" in text
    assert "docs\\planning-workbook-contract.md" in text or (
        "docs/planning-workbook-contract.md" in text
    )
    assert "Production_Plan" in text
    assert "Output_Requests" in text
    assert "Run metadata must be entered explicitly" in text


def test_inspect_workbook_contract_reports_required_sheet_counts(tmp_path):
    workbook_path = tmp_path / "planning-input.xlsx"
    write_e2e_planning_workbook(workbook_path)

    inspection = inspect_workbook_contract(workbook_path)
    text = format_workbook_contract_inspection(inspection)

    assert inspection.is_valid is True
    assert inspection.missing_sheet_names == ()
    assert ("Production_Plan", 3) in inspection.sheet_row_counts
    assert "Workbook contract check passed" in text
    assert "Production_Plan: 3 rows" in text


def test_inspect_workbook_contract_reports_missing_required_sheets(tmp_path):
    report_path = tmp_path / "planning-run-report.xlsx"
    report_json = (
        FIXTURE_DIR / "expected_planning_run_report_snapshot.json"
    ).read_text(encoding="utf-8")
    write_planning_run_report_xlsx(report_json, report_path)

    inspection = inspect_workbook_contract(report_path)
    text = format_workbook_contract_inspection(inspection)

    assert inspection.is_valid is False
    assert "Production_Plan" in inspection.missing_sheet_names
    assert "Workbook contract check failed" in text
    assert "Missing required sheets:" in text
    assert "Production_Plan" in text


def test_format_summary_lines_shows_deterministic_planning_counts():
    summary = _summary()

    lines = format_summary_lines(summary)

    assert "Calculation authority: DETERMINISTIC_ENGINE" in lines
    assert (
        "Deferred capabilities: DUE_DATE_SCHEDULING, STANDARD_TIME_CALCULATION"
        in lines
    )
    assert "Recipe matching: 2 matched, 1 missing, 0 ambiguous, 1 T.B.D rows" in lines
    assert "Skipped scenarios: SCN-AI-DRAFT" in lines
    assert any("1. SCN-BASE | score 11400" in line for line in lines)
    assert any("SCN-BASE | HYDRAULIC | CUTTING" in line for line in lines)


def test_format_run_summary_includes_generated_paths_and_summary():
    result = PlanningWorkbookRunResult(
        input_workbook_path=Path("planning-input.xlsx"),
        json_output_path=Path("planning-report.json"),
        report_workbook_output_path=Path("planning-report.xlsx"),
        report_snapshot_json="{}",
        summary=_summary(),
    )

    text = format_run_summary(result)

    assert "Run complete" in text
    assert "Input workbook: planning-input.xlsx" in text
    assert "JSON report: planning-report.json" in text
    assert "Report workbook: planning-report.xlsx" in text
    assert "Calculation authority: DETERMINISTIC_ENGINE" in text


def _summary():
    return PlanningWorkbookRunSummary(
        calculation_authority="DETERMINISTIC_ENGINE",
        deferred_capabilities=(
            "DUE_DATE_SCHEDULING",
            "STANDARD_TIME_CALCULATION",
        ),
        total_plan_line_count=3,
        matched_count=2,
        missing_count=1,
        ambiguous_count=0,
        tbd_report_row_count=1,
        skipped_scenario_ids=("SCN-AI-DRAFT",),
        ranked_scenarios=(
            PlanningWorkbookScenarioSummary(
                rank=1,
                scenario_id="SCN-BASE",
                scenario_name="Baseline",
                priority_rule="SHORTEST_LEAD_TIME_PROXY",
                deterministic_score=11400.0,
                missing_recipe_count=1,
                ambiguous_recipe_count=0,
                unplannable_line_count=1,
                risk_score_total=400.0,
                bottleneck_risk_signals=("PROXY_LOAD",),
            ),
        ),
        top_bottleneck_risks=(
            PlanningWorkbookBottleneckRiskSummary(
                scenario_id="SCN-BASE",
                domain_code="HYDRAULIC",
                process_group="CUTTING",
                equipment_group="HYD-CUT-01",
                risk_level="LOW",
                risk_score=120.0,
                signals=("PROXY_LOAD",),
            ),
        ),
    )


def _complete_inputs():
    return PlanningLauncherInputs(
        input_workbook_path="planning-input.xlsx",
        json_output_path="planning-report.json",
        report_workbook_output_path="",
        plan_batch_id="PLAN-2026-07-M",
        plan_period="2026-07",
        plan_type="MONTHLY",
        work_order_import_batch_id="WO-HISTORY-2026-06",
        equipment_snapshot_batch_id="EQ-SNAPSHOT-2026-07-01",
        equipment_snapshot_at="2026-07-01T08:00:00",
        tbd_import_batch_id="TBD-2026-07",
        engine_version="planning-core-ui-v1",
    )
