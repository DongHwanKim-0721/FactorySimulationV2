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

    exit_code = main(
        [
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
    )

    captured = capsys.readouterr()

    assert exit_code == 0
    assert captured.err == ""
    assert captured.out == ""
    assert report_path.read_text(encoding="utf-8") == (
        FIXTURE_DIR / "expected_planning_run_report_snapshot.json"
    ).read_text(encoding="utf-8")
