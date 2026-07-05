from __future__ import annotations

from collections import Counter
import json
from typing import Mapping, Protocol

from .fixtures import PlanningFixtureSet
from .load_risk import BottleneckRiskRow, LoadAndRiskReport, LoadSummaryRow, LoadTotalRow
from .recipe_matching import (
    MissingRecipeReportRow,
    RecipeMatchingResult,
    RecipePlanMatch,
)
from .scenario_planning import ScenarioComparisonResult


class _SourceRowRecord(Protocol):
    source_row_id: str


def render_fixture_report_snapshot(fixture_set: PlanningFixtureSet) -> str:
    report = {
        "ai_role": "DRAFTS_AND_RECOMMENDATIONS_ONLY",
        "calculation_authority": "DETERMINISTIC_ENGINE",
        "contract_counts": {
            "domains": len(fixture_set.domains),
            "equipment_snapshots": len(fixture_set.equipment_snapshots),
            "production_plan_lines": len(fixture_set.production_plan_lines),
            "recipe_headers": len(fixture_set.recipe_headers),
            "recipe_steps": len(fixture_set.recipe_steps),
            "scenario_definitions": len(fixture_set.scenario_definitions),
            "work_order_operations": len(fixture_set.work_order_operations),
        },
        "deferred_capabilities": [
            "DUE_DATE_SCHEDULING",
            "STANDARD_TIME_CALCULATION",
        ],
        "domain_labels_by_code": {
            domain.domain_code: domain.domain_label
            for domain in sorted(
                fixture_set.domains,
                key=lambda domain: domain.domain_code,
            )
        },
        "fixture_contract_version": 1,
        "planning_boundary": "PRODUCTION_PLANNING_CORE_ONLY",
        "prototype_dependency": "NONE",
        "scenario_execution": {
            "draft_only": sorted(
                scenario.scenario_id
                for scenario in fixture_set.scenario_definitions
                if not scenario.is_executable
            ),
            "executable": sorted(
                scenario.scenario_id
                for scenario in fixture_set.scenario_definitions
                if scenario.is_executable
            ),
        },
        "source_row_ids": {
            "equipment_snapshots": _source_row_ids(fixture_set.equipment_snapshots),
            "production_plan_lines": _source_row_ids(
                fixture_set.production_plan_lines
            ),
            "recipe_headers": _source_row_ids(fixture_set.recipe_headers),
            "recipe_steps": _source_row_ids(fixture_set.recipe_steps),
            "scenario_definitions": _source_row_ids(
                fixture_set.scenario_definitions
            ),
            "work_order_operations": _source_row_ids(
                fixture_set.work_order_operations
            ),
        },
    }
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def render_planning_run_report_snapshot(
    *,
    matching_result: RecipeMatchingResult,
    scenario_reports: Mapping[str, LoadAndRiskReport],
    scenario_comparison: ScenarioComparisonResult,
) -> str:
    report = {
        "ai_role": "DRAFTS_AND_RECOMMENDATIONS_ONLY",
        "calculation_authority": "DETERMINISTIC_ENGINE",
        "deferred_capabilities": [
            "DUE_DATE_SCHEDULING",
            "STANDARD_TIME_CALCULATION",
        ],
        "fixture_contract_version": 2,
        "planning_boundary": "PRODUCTION_PLANNING_CORE_ONLY",
        "prototype_dependency": "NONE",
        "recipe_matching": {
            "match_status_counts": _match_status_counts(matching_result),
            "matches": [
                _recipe_match_row(match)
                for match in sorted(
                    matching_result.matches,
                    key=lambda match: match.plan_source_row_id,
                )
            ],
            "tbd_report_rows": [
                _missing_recipe_row(row)
                for row in sorted(
                    matching_result.tbd_report_rows,
                    key=lambda row: row.plan_source_row_id,
                )
            ],
        },
        "scenario_comparison": {
            "engine_version": scenario_comparison.engine_version,
            "ranked_scenarios": [
                {
                    "ai_explanation": row.ai_explanation,
                    "ambiguous_recipe_count": row.ambiguous_recipe_count,
                    "bottleneck_risk_signals": list(row.bottleneck_risk_signals),
                    "deterministic_metrics": row.deterministic_metrics,
                    "deterministic_score": row.deterministic_score,
                    "missing_recipe_count": row.missing_recipe_count,
                    "priority_rule": row.priority_rule,
                    "rank": row.rank,
                    "ranking_reasons": list(row.ranking_reasons),
                    "scenario_id": row.scenario_id,
                    "scenario_name": row.scenario_name,
                    "unplannable_line_count": row.unplannable_line_count,
                }
                for row in scenario_comparison.rows
            ],
            "skipped_scenario_ids": list(scenario_comparison.skipped_scenario_ids),
        },
        "scenario_reports": {
            scenario_id: _load_and_risk_report_row(report)
            for scenario_id, report in sorted(scenario_reports.items())
        },
    }
    return json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _source_row_ids(records: tuple[_SourceRowRecord, ...]) -> list[str]:
    return [record.source_row_id for record in records]


def _match_status_counts(matching_result: RecipeMatchingResult) -> dict[str, int]:
    return dict(sorted(Counter(match.status for match in matching_result.matches).items()))


def _recipe_match_row(match: RecipePlanMatch) -> dict[str, object]:
    return {
        "candidate_recipe_ids": list(match.candidate_recipe_ids),
        "deprecated_recipe_ids": list(match.deprecated_recipe_ids),
        "domain_code": match.domain_code,
        "item_code": match.item_code,
        "plan_source_row_id": match.plan_source_row_id,
        "reason": match.reason,
        "selected_recipe_id": match.selected_recipe_id,
        "status": match.status,
        "tbd_recipe_ids": list(match.tbd_recipe_ids),
    }


def _missing_recipe_row(row: MissingRecipeReportRow) -> dict[str, object]:
    return {
        "customer_name": row.customer_name,
        "customer_order_ref": row.customer_order_ref,
        "domain_code": row.domain_code,
        "item_code": row.item_code,
        "item_name": row.item_name,
        "plan_batch_id": row.plan_batch_id,
        "plan_source_row_id": row.plan_source_row_id,
        "reason": row.reason,
    }


def _load_and_risk_report_row(report: LoadAndRiskReport) -> dict[str, object]:
    return {
        "ambiguous_recipe_count": report.ambiguous_recipe_count,
        "bottleneck_risks": [
            _bottleneck_risk_row(risk)
            for risk in sorted(
                report.bottleneck_risks,
                key=lambda risk: (
                    risk.domain_code,
                    risk.process_group,
                    risk.equipment_group,
                ),
            )
        ],
        "is_precise_lead_time": report.is_precise_lead_time,
        "load_summary_rows": [
            _load_summary_row(row)
            for row in sorted(
                report.load_summary_rows,
                key=lambda row: (
                    row.domain_code,
                    row.process_group,
                    row.equipment_group,
                    row.recipe_id,
                    row.recipe_step_no,
                ),
            )
        ],
        "load_totals": [
            _load_total_row(row)
            for row in sorted(
                report.load_totals,
                key=lambda row: (row.scope, row.domain_code),
            )
        ],
        "missing_recipe_count": report.missing_recipe_count,
        "proxy_label": report.proxy_label,
        "timing_basis": report.timing_basis,
        "unplannable_line_count": report.unplannable_line_count,
    }


def _load_summary_row(row: LoadSummaryRow) -> dict[str, object]:
    return {
        "domain_code": row.domain_code,
        "equipment_group": row.equipment_group,
        "order_quantity_total": row.order_quantity_total,
        "plan_source_row_ids": list(row.plan_source_row_ids),
        "process_group": row.process_group,
        "proxy_load_units": row.proxy_load_units,
        "recipe_id": row.recipe_id,
        "recipe_step_no": row.recipe_step_no,
        "weight_total": row.weight_total,
    }


def _load_total_row(row: LoadTotalRow) -> dict[str, object]:
    return {
        "domain_code": row.domain_code,
        "proxy_load_units": row.proxy_load_units,
        "scope": row.scope,
    }


def _bottleneck_risk_row(row: BottleneckRiskRow) -> dict[str, object]:
    return {
        "domain_code": row.domain_code,
        "equipment_group": row.equipment_group,
        "process_group": row.process_group,
        "proxy_load_units": row.proxy_load_units,
        "risk_level": row.risk_level,
        "risk_score": row.risk_score,
        "signals": list(row.signals),
    }
