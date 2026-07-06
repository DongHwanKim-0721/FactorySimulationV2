from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any, Mapping

from .planning_workbook_io import (
    PlanningWorkbookRunConfig,
    render_planning_workbook_report_snapshot,
    write_planning_run_report_xlsx,
    write_planning_workbook_template_xlsx,
)


REQUIRED_RUN_METADATA_FIELDS = (
    "plan_batch_id",
    "plan_period",
    "plan_type",
    "work_order_import_batch_id",
    "equipment_snapshot_batch_id",
    "equipment_snapshot_at",
    "tbd_import_batch_id",
    "engine_version",
)


@dataclass(frozen=True)
class PlanningWorkbookTemplateResult:
    workbook_path: Path
    include_examples: bool


@dataclass(frozen=True)
class PlanningWorkbookRunRequest:
    input_workbook_path: str | Path
    config: PlanningWorkbookRunConfig
    json_output_path: str | Path | None = None
    report_workbook_output_path: str | Path | None = None


@dataclass(frozen=True)
class PlanningWorkbookScenarioSummary:
    rank: int
    scenario_id: str
    scenario_name: str
    priority_rule: str
    deterministic_score: float
    missing_recipe_count: int
    ambiguous_recipe_count: int
    unplannable_line_count: int
    risk_score_total: float
    bottleneck_risk_signals: tuple[str, ...]


@dataclass(frozen=True)
class PlanningWorkbookBottleneckRiskSummary:
    scenario_id: str
    domain_code: str
    process_group: str
    equipment_group: str
    risk_level: str
    risk_score: float
    signals: tuple[str, ...]


@dataclass(frozen=True)
class PlanningWorkbookRunSummary:
    calculation_authority: str
    deferred_capabilities: tuple[str, ...]
    total_plan_line_count: int
    matched_count: int
    missing_count: int
    ambiguous_count: int
    tbd_report_row_count: int
    skipped_scenario_ids: tuple[str, ...]
    ranked_scenarios: tuple[PlanningWorkbookScenarioSummary, ...]
    top_bottleneck_risks: tuple[PlanningWorkbookBottleneckRiskSummary, ...]


@dataclass(frozen=True)
class PlanningWorkbookRunResult:
    input_workbook_path: Path
    json_output_path: Path | None
    report_workbook_output_path: Path | None
    report_snapshot_json: str
    summary: PlanningWorkbookRunSummary


class PlanningWorkbookRunRequestError(ValueError):
    pass


def create_planning_workbook_template(
    output_path: str | Path,
    *,
    blank: bool = False,
) -> PlanningWorkbookTemplateResult:
    path = _required_path(output_path, "template output path")
    include_examples = not blank
    write_planning_workbook_template_xlsx(path, include_examples=include_examples)
    return PlanningWorkbookTemplateResult(
        workbook_path=path,
        include_examples=include_examples,
    )


def run_planning_workbook(
    request: PlanningWorkbookRunRequest,
) -> PlanningWorkbookRunResult:
    normalized = _normalize_run_request(request)
    snapshot = render_planning_workbook_report_snapshot(
        normalized.input_workbook_path,
        config=request.config,
    )

    if normalized.json_output_path is not None:
        normalized.json_output_path.write_text(snapshot, encoding="utf-8")
    if normalized.report_workbook_output_path is not None:
        write_planning_run_report_xlsx(
            snapshot,
            normalized.report_workbook_output_path,
        )

    return PlanningWorkbookRunResult(
        input_workbook_path=normalized.input_workbook_path,
        json_output_path=normalized.json_output_path,
        report_workbook_output_path=normalized.report_workbook_output_path,
        report_snapshot_json=snapshot,
        summary=summarize_planning_workbook_report(snapshot),
    )


def summarize_planning_workbook_report(
    report_snapshot_json: str,
    *,
    bottleneck_limit: int = 5,
) -> PlanningWorkbookRunSummary:
    report = json.loads(report_snapshot_json)
    recipe_matching = report["recipe_matching"]
    status_counts = recipe_matching["match_status_counts"]
    scenario_comparison = report["scenario_comparison"]

    return PlanningWorkbookRunSummary(
        calculation_authority=report["calculation_authority"],
        deferred_capabilities=tuple(report["deferred_capabilities"]),
        total_plan_line_count=len(recipe_matching["matches"]),
        matched_count=int(status_counts.get("MATCHED", 0)),
        missing_count=int(status_counts.get("MISSING", 0)),
        ambiguous_count=int(status_counts.get("AMBIGUOUS", 0)),
        tbd_report_row_count=len(recipe_matching["tbd_report_rows"]),
        skipped_scenario_ids=tuple(scenario_comparison["skipped_scenario_ids"]),
        ranked_scenarios=_scenario_summaries(scenario_comparison),
        top_bottleneck_risks=_top_bottleneck_risks(
            report["scenario_reports"],
            limit=bottleneck_limit,
        ),
    )


@dataclass(frozen=True)
class _NormalizedPlanningWorkbookRunRequest:
    input_workbook_path: Path
    json_output_path: Path | None
    report_workbook_output_path: Path | None


def _normalize_run_request(
    request: PlanningWorkbookRunRequest,
) -> _NormalizedPlanningWorkbookRunRequest:
    input_workbook_path = _required_path(
        request.input_workbook_path,
        "input workbook path",
    )
    json_output_path = _optional_path(
        request.json_output_path,
        "JSON output path",
    )
    report_workbook_output_path = _optional_path(
        request.report_workbook_output_path,
        "report workbook output path",
    )
    missing_fields = _missing_run_metadata_fields(request.config)

    errors: list[str] = []
    if missing_fields:
        errors.append("missing run metadata: " + ", ".join(missing_fields))
    if json_output_path is None and report_workbook_output_path is None:
        errors.append("at least one report output path is required")
    if errors:
        raise PlanningWorkbookRunRequestError("; ".join(errors))

    return _NormalizedPlanningWorkbookRunRequest(
        input_workbook_path=input_workbook_path,
        json_output_path=json_output_path,
        report_workbook_output_path=report_workbook_output_path,
    )


def _missing_run_metadata_fields(
    config: PlanningWorkbookRunConfig,
) -> tuple[str, ...]:
    return tuple(
        field
        for field in REQUIRED_RUN_METADATA_FIELDS
        if not str(getattr(config, field)).strip()
    )


def _required_path(path: str | Path, field_name: str) -> Path:
    if not str(path).strip():
        raise PlanningWorkbookRunRequestError(f"{field_name} is required")
    return Path(path)


def _optional_path(path: str | Path | None, field_name: str) -> Path | None:
    if path is None:
        return None
    return _required_path(path, field_name)


def _scenario_summaries(
    scenario_comparison: Mapping[str, Any],
) -> tuple[PlanningWorkbookScenarioSummary, ...]:
    return tuple(
        PlanningWorkbookScenarioSummary(
            rank=int(row["rank"]),
            scenario_id=row["scenario_id"],
            scenario_name=row["scenario_name"],
            priority_rule=row["priority_rule"],
            deterministic_score=float(row["deterministic_score"]),
            missing_recipe_count=int(row["missing_recipe_count"]),
            ambiguous_recipe_count=int(row["ambiguous_recipe_count"]),
            unplannable_line_count=int(row["unplannable_line_count"]),
            risk_score_total=float(
                row["deterministic_metrics"].get("risk_score_total", 0.0)
            ),
            bottleneck_risk_signals=tuple(row["bottleneck_risk_signals"]),
        )
        for row in scenario_comparison["ranked_scenarios"]
    )


def _top_bottleneck_risks(
    scenario_reports: Mapping[str, Any],
    *,
    limit: int,
) -> tuple[PlanningWorkbookBottleneckRiskSummary, ...]:
    risks = [
        PlanningWorkbookBottleneckRiskSummary(
            scenario_id=scenario_id,
            domain_code=row["domain_code"],
            process_group=row["process_group"],
            equipment_group=row["equipment_group"],
            risk_level=row["risk_level"],
            risk_score=float(row["risk_score"]),
            signals=tuple(row["signals"]),
        )
        for scenario_id, scenario_report in scenario_reports.items()
        for row in scenario_report["bottleneck_risks"]
    ]
    return tuple(
        sorted(
            risks,
            key=lambda risk: (
                -risk.risk_score,
                risk.scenario_id,
                risk.domain_code,
                risk.process_group,
                risk.equipment_group,
            ),
        )[:limit]
    )
