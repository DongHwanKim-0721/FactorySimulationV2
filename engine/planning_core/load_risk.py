from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping

from .contracts import EquipmentSnapshot, ProductionPlanLine, RecipeStep
from .recipe_matching import RecipeMatchingResult


PROXY_LABEL = "SHORTEST_LEAD_TIME_PROXY"
TIMING_BASIS = "NO_STANDARD_TIMES"


@dataclass(frozen=True)
class LoadSummaryRow:
    domain_code: str
    process_group: str
    equipment_group: str
    recipe_id: str
    recipe_step_no: int
    plan_source_row_ids: tuple[str, ...]
    order_quantity_total: float
    weight_total: float
    proxy_load_units: float


@dataclass(frozen=True)
class LoadTotalRow:
    scope: str
    domain_code: str
    proxy_load_units: float


@dataclass(frozen=True)
class BottleneckRiskRow:
    domain_code: str
    process_group: str
    equipment_group: str
    proxy_load_units: float
    risk_level: str
    risk_score: float
    signals: tuple[str, ...]


@dataclass(frozen=True)
class LoadAndRiskReport:
    proxy_label: str
    timing_basis: str
    is_precise_lead_time: bool
    load_summary_rows: tuple[LoadSummaryRow, ...]
    load_totals: tuple[LoadTotalRow, ...]
    bottleneck_risks: tuple[BottleneckRiskRow, ...]
    missing_recipe_count: int
    ambiguous_recipe_count: int
    unplannable_line_count: int


def generate_load_and_risk_report(
    *,
    plan_lines: tuple[ProductionPlanLine, ...] | list[ProductionPlanLine],
    matching_result: RecipeMatchingResult,
    recipe_steps: tuple[RecipeStep, ...] | list[RecipeStep],
    equipment_snapshots: tuple[EquipmentSnapshot, ...] | list[EquipmentSnapshot],
    equipment_overrides: Mapping[str, bool] | None = None,
) -> LoadAndRiskReport:
    plan_by_source_row_id = {
        plan_line.source_row_id: plan_line
        for plan_line in plan_lines
    }
    steps_by_recipe_key: dict[tuple[str, str], list[RecipeStep]] = {}
    for step in recipe_steps:
        steps_by_recipe_key.setdefault((step.domain_code, step.recipe_id), []).append(step)

    rows: list[LoadSummaryRow] = []
    unplannable_plan_rows: set[str] = set()

    for match in matching_result.matches:
        if match.status != "MATCHED":
            unplannable_plan_rows.add(match.plan_source_row_id)
            continue

        plan_line = plan_by_source_row_id[match.plan_source_row_id]
        steps = sorted(
            steps_by_recipe_key.get((match.domain_code, match.selected_recipe_id), []),
            key=lambda step: (step.step_no, step.source_row_id),
        )
        if not steps:
            unplannable_plan_rows.add(match.plan_source_row_id)
            continue

        for step in steps:
            rows.append(_load_row(plan_line, step))

    load_summary_rows = _aggregate_load_rows(rows)

    return LoadAndRiskReport(
        proxy_label=PROXY_LABEL,
        timing_basis=TIMING_BASIS,
        is_precise_lead_time=False,
        load_summary_rows=load_summary_rows,
        load_totals=_load_totals(load_summary_rows),
        bottleneck_risks=_bottleneck_risks(
            load_summary_rows,
            equipment_snapshots,
            equipment_overrides or {},
        ),
        missing_recipe_count=sum(
            1 for match in matching_result.matches if match.status == "MISSING"
        ),
        ambiguous_recipe_count=sum(
            1 for match in matching_result.matches if match.status == "AMBIGUOUS"
        ),
        unplannable_line_count=len(unplannable_plan_rows),
    )


def _load_row(plan_line: ProductionPlanLine, step: RecipeStep) -> LoadSummaryRow:
    weight = plan_line.weight or 0
    proxy_load_units = (
        (plan_line.order_quantity * step.quantity_factor)
        + (weight * step.weight_factor)
    ) * step.repeat_count
    return LoadSummaryRow(
        domain_code=plan_line.domain_code,
        process_group=step.process_group,
        equipment_group=step.preferred_equipment or step.process_group,
        recipe_id=step.recipe_id,
        recipe_step_no=step.step_no,
        plan_source_row_ids=(plan_line.source_row_id,),
        order_quantity_total=plan_line.order_quantity,
        weight_total=weight,
        proxy_load_units=proxy_load_units,
    )


def _load_totals(rows: tuple[LoadSummaryRow, ...]) -> tuple[LoadTotalRow, ...]:
    totals_by_domain: dict[str, float] = {}
    for row in rows:
        totals_by_domain[row.domain_code] = (
            totals_by_domain.get(row.domain_code, 0) + row.proxy_load_units
        )

    domain_totals = [
        LoadTotalRow("DOMAIN", domain_code, proxy_load_units)
        for domain_code, proxy_load_units in sorted(totals_by_domain.items())
    ]
    whole_factory_total = sum(row.proxy_load_units for row in rows)
    return tuple(
        domain_totals
        + [LoadTotalRow("WHOLE_FACTORY", "ALL", whole_factory_total)]
    )


def _aggregate_load_rows(rows: list[LoadSummaryRow]) -> tuple[LoadSummaryRow, ...]:
    aggregate: dict[tuple[str, str, str, str, int], LoadSummaryRow] = {}
    for row in rows:
        key = (
            row.domain_code,
            row.process_group,
            row.equipment_group,
            row.recipe_id,
            row.recipe_step_no,
        )
        existing = aggregate.get(key)
        if existing is None:
            aggregate[key] = row
            continue
        aggregate[key] = LoadSummaryRow(
            domain_code=row.domain_code,
            process_group=row.process_group,
            equipment_group=row.equipment_group,
            recipe_id=row.recipe_id,
            recipe_step_no=row.recipe_step_no,
            plan_source_row_ids=tuple(
                sorted(existing.plan_source_row_ids + row.plan_source_row_ids)
            ),
            order_quantity_total=(
                existing.order_quantity_total + row.order_quantity_total
            ),
            weight_total=existing.weight_total + row.weight_total,
            proxy_load_units=existing.proxy_load_units + row.proxy_load_units,
        )

    return tuple(
        sorted(
            aggregate.values(),
            key=lambda row: (
                row.domain_code,
                row.process_group,
                row.equipment_group,
                row.recipe_id,
                row.recipe_step_no,
            ),
        )
    )


def _bottleneck_risks(
    rows: tuple[LoadSummaryRow, ...],
    equipment_snapshots: tuple[EquipmentSnapshot, ...] | list[EquipmentSnapshot],
    equipment_overrides: Mapping[str, bool],
) -> tuple[BottleneckRiskRow, ...]:
    snapshot_availability = _snapshot_availability_by_equipment(equipment_snapshots)
    risks: list[BottleneckRiskRow] = []
    for row in rows:
        signals = ["PROXY_LOAD"]
        is_unavailable = False

        snapshot_available = snapshot_availability.get(
            (row.domain_code, row.equipment_group)
        )
        if snapshot_available is False:
            is_unavailable = True
            signals.append("SNAPSHOT_UNAVAILABLE")

        if equipment_overrides.get(row.equipment_group) is False:
            is_unavailable = True
            signals.append("OVERRIDE_UNAVAILABLE")

        risk_score = row.proxy_load_units * (2 if is_unavailable else 1)
        risks.append(
            BottleneckRiskRow(
                domain_code=row.domain_code,
                process_group=row.process_group,
                equipment_group=row.equipment_group,
                proxy_load_units=row.proxy_load_units,
                risk_level="HIGH" if is_unavailable else "LOW",
                risk_score=risk_score,
                signals=tuple(signals),
            )
        )
    return tuple(
        sorted(
            risks,
            key=lambda risk: (
                risk.domain_code,
                risk.process_group,
                risk.equipment_group,
            ),
        )
    )


def _snapshot_availability_by_equipment(
    equipment_snapshots: tuple[EquipmentSnapshot, ...] | list[EquipmentSnapshot],
) -> dict[tuple[str, str], bool]:
    availability: dict[tuple[str, str], bool] = {}
    for snapshot in equipment_snapshots:
        availability[(snapshot.domain_code, snapshot.equipment_id)] = snapshot.is_available
        availability[(snapshot.domain_code, snapshot.equipment_name)] = snapshot.is_available
    return availability
