from engine.planning_core import (
    PLANNING_WORKBOOK_HEADERS,
    PLANNING_WORKBOOK_SHEETS,
    REPORT_WORKBOOK_SHEETS,
    load_planning_workbook_rows,
    load_xlsx_sheet_rows,
)
from engine.planning_core.cli import main
from planning_workbook_test_utils import (
    ENGINE_VERSION,
    FIXTURE_DIR,
    write_e2e_planning_workbook,
)


def test_cli_run_workbook_writes_deterministic_report_json(tmp_path, capsys):
    workbook_path = tmp_path / "planning-input.xlsx"
    report_path = tmp_path / "planning-run-report.json"
    write_e2e_planning_workbook(workbook_path)

    exit_code = main(_run_workbook_args(workbook_path, report_path))

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == ""
    assert report_path.read_text(encoding="utf-8") == (
        FIXTURE_DIR / "expected_planning_run_report_snapshot.json"
    ).read_text(encoding="utf-8")


def test_cli_run_workbook_writes_deterministic_report_xlsx(tmp_path, capsys):
    workbook_path = tmp_path / "planning-input.xlsx"
    report_path = tmp_path / "planning-run-report.xlsx"
    write_e2e_planning_workbook(workbook_path)

    exit_code = main(_run_workbook_args(workbook_path, report_path))

    captured = capsys.readouterr()
    report_rows = load_xlsx_sheet_rows(report_path)

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == ""
    assert set(report_rows) == set(REPORT_WORKBOOK_SHEETS.values())
    assert report_rows["Recipe_Matching"][0]["plan_source_row_id"] == "plan-row-2"
    assert report_rows["Recipe_Matching"][2]["status"] == "MISSING"
    assert report_rows["TBD_Report"][0]["item_code"] == "SHP-300"
    assert report_rows["Load_Summary"][0]["scenario_id"] == "SCN-BASE"
    assert report_rows["Bottleneck_Risk"][2]["signals"] == (
        "PROXY_LOAD; SNAPSHOT_UNAVAILABLE"
    )
    assert report_rows["Scenario_Comparison"][0]["scenario_id"] == "SCN-BASE"
    assert report_rows["Run_Metadata"][0]["key"] == "ai_role"


def test_cli_create_template_writes_runnable_sample_workbook(tmp_path, capsys):
    workbook_path = tmp_path / "planning-input-template.xlsx"
    report_path = tmp_path / "planning-run-report.json"

    exit_code = main(["create-template", "--out", str(workbook_path)])
    created = capsys.readouterr()

    workbook_rows = load_planning_workbook_rows(workbook_path)
    sheet_rows = load_xlsx_sheet_rows(workbook_path)
    run_exit_code = main(_run_workbook_args(workbook_path, report_path))
    ran = capsys.readouterr()

    assert exit_code == 0
    assert created.err == ""
    assert created.out == ""
    assert set(sheet_rows) == set(PLANNING_WORKBOOK_SHEETS.values())
    assert workbook_rows.production_plan_rows[0]["item_code"] == "HYD-100"
    assert workbook_rows.scenario_recipe_override_rows == ()
    assert run_exit_code == 0
    assert ran.err == ""
    assert ran.out == ""
    assert '"calculation_authority": "DETERMINISTIC_ENGINE"' in report_path.read_text(
        encoding="utf-8"
    )


def test_cli_create_blank_template_writes_headers_only(tmp_path, capsys):
    workbook_path = tmp_path / "blank-planning-input-template.xlsx"

    exit_code = main(["create-template", "--out", str(workbook_path), "--blank"])
    captured = capsys.readouterr()
    sheet_rows = load_xlsx_sheet_rows(workbook_path)

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == ""
    assert set(sheet_rows) == set(PLANNING_WORKBOOK_SHEETS.values())
    assert all(rows == () for rows in sheet_rows.values())
    assert set(PLANNING_WORKBOOK_HEADERS) == set(PLANNING_WORKBOOK_SHEETS.values())


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
