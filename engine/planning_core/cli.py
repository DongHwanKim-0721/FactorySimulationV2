from __future__ import annotations

import argparse
from pathlib import Path
import sys
from typing import Sequence

from .planning_workbook_io import (
    PlanningWorkbookError,
    PlanningWorkbookRunConfig,
    PlanningWorkbookValidationError,
    render_planning_workbook_report_snapshot,
    write_planning_run_report_xlsx,
    write_planning_workbook_template_xlsx,
)


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "create-template":
        return _create_template(args)
    if args.command == "run-workbook":
        return _run_workbook(args)
    parser.print_help(sys.stderr)
    return 2


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m engine.planning_core.cli",
        description="Run deterministic production-planning core workflows.",
    )
    subparsers = parser.add_subparsers(dest="command")

    create_template = subparsers.add_parser(
        "create-template",
        help="Write a planning input workbook template.",
    )
    create_template.add_argument(
        "--out",
        required=True,
        help="Output planning input workbook .xlsx path.",
    )
    create_template.add_argument(
        "--blank",
        action="store_true",
        help="Write headers only, without sample planning rows.",
    )

    run_workbook = subparsers.add_parser(
        "run-workbook",
        help="Read a planning workbook and write a deterministic report.",
    )
    run_workbook.add_argument("workbook", help="Input planning workbook .xlsx path.")
    run_workbook.add_argument(
        "--out",
        required=True,
        help="Output report path. Use .xlsx for an Excel workbook, or '-' for JSON stdout.",
    )
    run_workbook.add_argument("--plan-batch-id", required=True)
    run_workbook.add_argument("--plan-period", required=True)
    run_workbook.add_argument("--plan-type", required=True)
    run_workbook.add_argument("--work-order-import-batch-id", required=True)
    run_workbook.add_argument("--equipment-snapshot-batch-id", required=True)
    run_workbook.add_argument("--equipment-snapshot-at", required=True)
    run_workbook.add_argument("--tbd-import-batch-id", required=True)
    run_workbook.add_argument("--engine-version", required=True)

    return parser


def _create_template(args: argparse.Namespace) -> int:
    try:
        write_planning_workbook_template_xlsx(
            args.out,
            include_examples=not args.blank,
        )
    except (OSError, PlanningWorkbookError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _run_workbook(args: argparse.Namespace) -> int:
    try:
        snapshot = render_planning_workbook_report_snapshot(
            Path(args.workbook),
            config=PlanningWorkbookRunConfig(
                plan_batch_id=args.plan_batch_id,
                plan_period=args.plan_period,
                plan_type=args.plan_type,
                work_order_import_batch_id=args.work_order_import_batch_id,
                equipment_snapshot_batch_id=args.equipment_snapshot_batch_id,
                equipment_snapshot_at=args.equipment_snapshot_at,
                tbd_import_batch_id=args.tbd_import_batch_id,
                engine_version=args.engine_version,
            ),
        )
        _write_report(args.out, snapshot)
    except PlanningWorkbookValidationError as exc:
        print(str(exc), file=sys.stderr)
        for stage, errors in sorted(exc.errors_by_stage.items()):
            for error in errors:
                print(f"{stage}: {error}", file=sys.stderr)
        return 2
    except (OSError, PlanningWorkbookError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    return 0


def _write_report(output_path: str, report_json: str) -> None:
    if output_path == "-":
        print(report_json, end="")
        return
    path = Path(output_path)
    if path.suffix.lower() == ".xlsx":
        write_planning_run_report_xlsx(report_json, path)
        return
    path.write_text(report_json, encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
