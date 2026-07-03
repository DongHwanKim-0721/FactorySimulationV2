from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import ScenarioDefinition
from .domains import normalize_domain_code
from .load_risk import LoadAndRiskReport, LoadSummaryRow


@dataclass(frozen=True)
class ScenarioValidationError:
    source_row_id: str
    field: str
    message: str
    raw_values: dict[str, Any]


@dataclass(frozen=True)
class ScenarioWorkbookImportResult:
    scenario_definitions: tuple[ScenarioDefinition, ...]
    errors: tuple[ScenarioValidationError, ...]


@dataclass(frozen=True)
class ScenarioComparisonRow:
    rank: int
    scenario_id: str
    scenario_name: str
    priority_rule: str
    deterministic_score: float
    deterministic_metrics: dict[str, float]
    ranking_reasons: tuple[str, ...]
    missing_recipe_count: int
    ambiguous_recipe_count: int
    unplannable_line_count: int
    load_summary_rows: tuple[LoadSummaryRow, ...]
    bottleneck_risk_signals: tuple[str, ...]
    ai_explanation: str


@dataclass(frozen=True)
class ScenarioComparisonResult:
    engine_version: str
    rows: tuple[ScenarioComparisonRow, ...]
    skipped_scenario_ids: tuple[str, ...]


@dataclass(frozen=True)
class _ScenarioRowError(Exception):
    field: str
    message: str


def import_scenario_workbook_rows(
    *,
    header_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    rule_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    equipment_override_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    priority_override_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    recipe_override_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    output_request_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    engine_version: str,
) -> ScenarioWorkbookImportResult:
    rules_by_scenario = {
        str(row.get("scenario_id") or "").strip(): dict(row)
        for row in rule_rows
        if str(row.get("scenario_id") or "").strip()
    }
    equipment_overrides = _equipment_overrides_by_scenario(equipment_override_rows)
    priority_overrides = _priority_overrides_by_scenario(priority_override_rows)
    recipe_overrides = _recipe_overrides_by_scenario(recipe_override_rows)
    output_requirements = _output_requirements_by_scenario(output_request_rows)

    scenarios: list[ScenarioDefinition] = []
    errors: list[ScenarioValidationError] = []

    for index, row in enumerate(header_rows, start=2):
        raw_values = dict(row)
        source_row_id = str(raw_values.get("source_row_id") or f"scenario-header-row-{index}")

        try:
            scenario_id = _required_text(raw_values, "scenario_id")
            rule_row = rules_by_scenario.get(scenario_id)
            if rule_row is None:
                raise _ScenarioRowError(
                    "priority_rule",
                    f"Missing scenario rule row for scenario: {scenario_id}",
                )
            priority_rule = _required_text(rule_row, "priority_rule")
            scenario_source = _required_text(raw_values, "scenario_source")
            scenarios.append(
                ScenarioDefinition(
                    scenario_id=scenario_id,
                    scenario_name=_required_text(raw_values, "scenario_name"),
                    scenario_source=scenario_source,
                    scope=_required_text(raw_values, "scope"),
                    included_plan_batch_ids=_parse_text_tuple(
                        raw_values.get("included_plan_batch_ids")
                    ),
                    domain_filters=_parse_domain_tuple(raw_values.get("domain_filters")),
                    priority_rule=priority_rule,
                    proxy_weights=_parse_weight_map(rule_row.get("proxy_weights")),
                    equipment_overrides=equipment_overrides.get(scenario_id, {}),
                    priority_overrides=priority_overrides.get(scenario_id, {}),
                    recipe_overrides=recipe_overrides.get(scenario_id, {}),
                    output_requirements=tuple(
                        sorted(
                            output_requirements.get(
                                scenario_id,
                                ("SCENARIO_COMPARISON",),
                            )
                        )
                    ),
                    engine_version=str(engine_version),
                    is_executable=(scenario_source != "AI_DRAFT"),
                    source_row_id=source_row_id,
                    raw_values=raw_values,
                )
            )
        except _ScenarioRowError as exc:
            errors.append(
                ScenarioValidationError(
                    source_row_id=source_row_id,
                    field=exc.field,
                    message=exc.message,
                    raw_values=raw_values,
                )
            )

    return ScenarioWorkbookImportResult(
        scenario_definitions=tuple(scenarios),
        errors=tuple(errors),
    )


def built_in_scenario_templates(*, engine_version: str) -> tuple[ScenarioDefinition, ...]:
    templates = (
        (
            "BUILT-IN-SHORTEST-LEAD-TIME-PROXY",
            "Shortest lead-time proxy",
            "SHORTEST_LEAD_TIME_PROXY",
            {"process_count": 1, "repeat_count": 1, "equipment_unavailable": 3},
        ),
        (
            "BUILT-IN-HEAVY-WEIGHT-FIRST",
            "Heavy weight first",
            "HEAVY_WEIGHT_FIRST",
            {"weight": -1, "equipment_unavailable": 3},
        ),
        (
            "BUILT-IN-CUSTOMER-PRIORITY",
            "Customer priority",
            "CUSTOMER_PRIORITY",
            {"customer_priority": -1, "equipment_unavailable": 3},
        ),
        (
            "BUILT-IN-EQUIPMENT-UNAVAILABLE",
            "Equipment unavailable",
            "EQUIPMENT_UNAVAILABLE",
            {"equipment_unavailable": 5, "process_count": 1},
        ),
        (
            "BUILT-IN-BOTTLENECK-AVOIDANCE",
            "Bottleneck avoidance",
            "BOTTLENECK_AVOIDANCE",
            {"bottleneck_risk": 5, "equipment_unavailable": 3},
        ),
    )
    return tuple(
        ScenarioDefinition(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            scenario_source="BUILT_IN",
            scope="WHOLE_FACTORY",
            included_plan_batch_ids=(),
            domain_filters=(),
            priority_rule=priority_rule,
            proxy_weights=proxy_weights,
            equipment_overrides={},
            priority_overrides={},
            recipe_overrides={},
            output_requirements=(
                "LOAD_SUMMARY",
                "BOTTLENECK_RISK_REPORT",
                "SCENARIO_COMPARISON",
            ),
            engine_version=str(engine_version),
            is_executable=True,
            source_row_id=scenario_id,
            raw_values={"template": scenario_id},
        )
        for scenario_id, scenario_name, priority_rule, proxy_weights in templates
    )


def compare_scenario_reports(
    *,
    scenarios: tuple[ScenarioDefinition, ...] | list[ScenarioDefinition],
    reports_by_scenario_id: Mapping[str, LoadAndRiskReport],
    engine_version: str,
) -> ScenarioComparisonResult:
    rows_with_score: list[tuple[float, str, ScenarioComparisonRow]] = []
    skipped_scenario_ids: list[str] = []

    for scenario in sorted(scenarios, key=lambda item: item.scenario_id):
        report = reports_by_scenario_id.get(scenario.scenario_id)
        if not scenario.is_executable or report is None:
            skipped_scenario_ids.append(scenario.scenario_id)
            continue

        risk_score_total = sum(risk.risk_score for risk in report.bottleneck_risks)
        deterministic_score = (
            (report.unplannable_line_count * 10000)
            + (report.missing_recipe_count * 1000)
            + (report.ambiguous_recipe_count * 500)
            + risk_score_total
        )
        metrics = {
            "ambiguous_recipe_count": report.ambiguous_recipe_count,
            "missing_recipe_count": report.missing_recipe_count,
            "risk_score_total": risk_score_total,
            "unplannable_line_count": report.unplannable_line_count,
        }
        rows_with_score.append(
            (
                deterministic_score,
                scenario.scenario_id,
                ScenarioComparisonRow(
                    rank=0,
                    scenario_id=scenario.scenario_id,
                    scenario_name=scenario.scenario_name,
                    priority_rule=scenario.priority_rule,
                    deterministic_score=deterministic_score,
                    deterministic_metrics=metrics,
                    ranking_reasons=(),
                    missing_recipe_count=report.missing_recipe_count,
                    ambiguous_recipe_count=report.ambiguous_recipe_count,
                    unplannable_line_count=report.unplannable_line_count,
                    load_summary_rows=report.load_summary_rows,
                    bottleneck_risk_signals=_bottleneck_risk_signals(report),
                    ai_explanation="",
                ),
            )
        )

    ranked_rows: list[ScenarioComparisonRow] = []
    for rank, (_, _, row) in enumerate(sorted(rows_with_score), start=1):
        ranked_rows.append(
            ScenarioComparisonRow(
                rank=rank,
                scenario_id=row.scenario_id,
                scenario_name=row.scenario_name,
                priority_rule=row.priority_rule,
                deterministic_score=row.deterministic_score,
                deterministic_metrics=row.deterministic_metrics,
                ranking_reasons=(
                    ("LOWEST_DETERMINISTIC_PROXY_SCORE",)
                    if rank == 1
                    else ("HIGHER_DETERMINISTIC_PROXY_SCORE",)
                ),
                missing_recipe_count=row.missing_recipe_count,
                ambiguous_recipe_count=row.ambiguous_recipe_count,
                unplannable_line_count=row.unplannable_line_count,
                load_summary_rows=row.load_summary_rows,
                bottleneck_risk_signals=row.bottleneck_risk_signals,
                ai_explanation=row.ai_explanation,
            )
        )

    return ScenarioComparisonResult(
        engine_version=str(engine_version),
        rows=tuple(ranked_rows),
        skipped_scenario_ids=tuple(sorted(skipped_scenario_ids)),
    )


def _equipment_overrides_by_scenario(
    rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
) -> dict[str, dict[str, bool]]:
    grouped: dict[str, dict[str, bool]] = {}
    for row in rows:
        scenario_id = str(row.get("scenario_id") or "").strip()
        equipment_id = str(row.get("equipment_id") or "").strip()
        if scenario_id and equipment_id:
            grouped.setdefault(scenario_id, {})[equipment_id] = _parse_bool(
                row.get("is_available"),
                default=True,
            )
    return grouped


def _bottleneck_risk_signals(report: LoadAndRiskReport) -> tuple[str, ...]:
    signals: list[str] = []
    for risk in report.bottleneck_risks:
        for signal in risk.signals:
            if signal not in signals:
                signals.append(signal)
    return tuple(signals)


def _priority_overrides_by_scenario(
    rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
) -> dict[str, dict[str, float]]:
    grouped: dict[str, dict[str, float]] = {}
    for row in rows:
        scenario_id = str(row.get("scenario_id") or "").strip()
        customer_name = str(row.get("customer_name") or "").strip()
        if scenario_id and customer_name:
            grouped.setdefault(scenario_id, {})[customer_name] = float(
                row.get("priority_boost") or 0
            )
    return grouped


def _recipe_overrides_by_scenario(
    rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
) -> dict[str, dict[tuple[str, str], str]]:
    grouped: dict[str, dict[tuple[str, str], str]] = {}
    for row in rows:
        scenario_id = str(row.get("scenario_id") or "").strip()
        item_code = str(row.get("item_code") or "").strip()
        recipe_id = str(row.get("recipe_id") or "").strip()
        if scenario_id and item_code and recipe_id:
            domain_code = _normalize_domain_code(row.get("domain") or "")
            grouped.setdefault(scenario_id, {})[(domain_code, item_code)] = recipe_id
    return grouped


def _output_requirements_by_scenario(
    rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
) -> dict[str, tuple[str, ...]]:
    grouped: dict[str, set[str]] = {}
    for row in rows:
        scenario_id = str(row.get("scenario_id") or "").strip()
        output_requirement = str(row.get("output_requirement") or "").strip()
        if scenario_id and output_requirement:
            grouped.setdefault(scenario_id, set()).add(output_requirement)
    return {
        scenario_id: tuple(sorted(requirements))
        for scenario_id, requirements in grouped.items()
    }


def _required_text(row: Mapping[str, Any], field: str) -> str:
    value = row.get(field)
    if value is None or str(value).strip() == "":
        raise _ScenarioRowError(field, f"Missing required scenario field: {field}")
    return str(value).strip()


def _parse_text_tuple(value: Any) -> tuple[str, ...]:
    if value is None or str(value).strip() == "":
        return ()
    if isinstance(value, list):
        return tuple(str(item).strip() for item in value if str(item).strip())
    return tuple(
        item.strip()
        for chunk in str(value).split(";")
        for item in chunk.split(",")
        if item.strip()
    )


def _parse_domain_tuple(value: Any) -> tuple[str, ...]:
    return tuple(_normalize_domain_code(value) for value in _parse_text_tuple(value))


def _parse_weight_map(value: Any) -> dict[str, float]:
    if value is None or str(value).strip() == "":
        return {}
    if isinstance(value, dict):
        return {str(key): float(weight) for key, weight in value.items()}

    weights: dict[str, float] = {}
    for token in _parse_text_tuple(value):
        key, separator, raw_weight = token.partition("=")
        if separator:
            weights[key.strip()] = float(raw_weight.strip())
    return weights


def _parse_bool(value: Any, *, default: bool) -> bool:
    if value is None or str(value).strip() == "":
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().upper()
    if normalized in {"TRUE", "YES", "Y", "1"}:
        return True
    if normalized in {"FALSE", "NO", "N", "0"}:
        return False
    raise _ScenarioRowError("is_available", f"Invalid scenario boolean value: {value}")


def _normalize_domain_code(value: Any) -> str:
    try:
        return normalize_domain_code(str(value))
    except ValueError as exc:
        raise _ScenarioRowError("domain", str(exc)) from exc
