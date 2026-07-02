from __future__ import annotations

import json
from typing import Protocol

from .fixtures import PlanningFixtureSet


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


def _source_row_ids(records: tuple[_SourceRowRecord, ...]) -> list[str]:
    return [record.source_row_id for record in records]
