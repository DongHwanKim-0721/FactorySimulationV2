from engine.planning_core import (
    BottleneckRiskRow,
    LoadAndRiskReport,
    LoadSummaryRow,
    LoadTotalRow,
    ScenarioDefinition,
    built_in_scenario_templates,
    compare_scenario_reports,
    import_scenario_workbook_rows,
)


def test_user_authored_scenario_workbook_rows_normalize_into_executable_definition():
    result = import_scenario_workbook_rows(
        header_rows=[
            {
                "source_row_id": "scenario-header-row-2",
                "scenario_id": "SCN-BASE",
                "scenario_name": "Baseline",
                "scenario_source": "USER_AUTHORED",
                "scope": "WHOLE_FACTORY",
                "included_plan_batch_ids": "PLAN-2026-07-M",
                "domain_filters": "HYDRAULIC;STS",
            }
        ],
        rule_rows=[
            {
                "source_row_id": "scenario-rule-row-2",
                "scenario_id": "SCN-BASE",
                "priority_rule": "SHORTEST_LEAD_TIME_PROXY",
                "proxy_weights": "process_count=1;equipment_unavailable=3;quantity=0.1",
            }
        ],
        equipment_override_rows=[
            {
                "scenario_id": "SCN-BASE",
                "equipment_id": "STS-POL-01",
                "is_available": "false",
            }
        ],
        priority_override_rows=[
            {
                "scenario_id": "SCN-BASE",
                "customer_name": "Acme",
                "priority_boost": "5",
            }
        ],
        recipe_override_rows=[
            {
                "scenario_id": "SCN-BASE",
                "domain": "STS",
                "item_code": "STS-200",
                "recipe_id": "R-STS-200",
            }
        ],
        output_request_rows=[
            {"scenario_id": "SCN-BASE", "output_requirement": "LOAD_SUMMARY"},
            {"scenario_id": "SCN-BASE", "output_requirement": "BOTTLENECK_RISK_REPORT"},
        ],
        engine_version="planning-core-test-v1",
    )

    assert result.errors == ()
    assert len(result.scenario_definitions) == 1

    scenario = result.scenario_definitions[0]
    assert scenario.scenario_id == "SCN-BASE"
    assert scenario.scenario_name == "Baseline"
    assert scenario.scenario_source == "USER_AUTHORED"
    assert scenario.scope == "WHOLE_FACTORY"
    assert scenario.included_plan_batch_ids == ("PLAN-2026-07-M",)
    assert scenario.domain_filters == ("HYDRAULIC", "STS")
    assert scenario.priority_rule == "SHORTEST_LEAD_TIME_PROXY"
    assert scenario.proxy_weights == {
        "process_count": 1,
        "equipment_unavailable": 3,
        "quantity": 0.1,
    }
    assert scenario.equipment_overrides == {"STS-POL-01": False}
    assert scenario.priority_overrides == {"Acme": 5}
    assert scenario.recipe_overrides == {("STS", "STS-200"): "R-STS-200"}
    assert scenario.output_requirements == (
        "BOTTLENECK_RISK_REPORT",
        "LOAD_SUMMARY",
    )
    assert scenario.engine_version == "planning-core-test-v1"
    assert scenario.is_executable is True
    assert scenario.source_row_id == "scenario-header-row-2"
    assert scenario.raw_values["scenario_id"] == "SCN-BASE"


def test_invalid_scenario_workbook_rows_report_errors_before_execution():
    result = import_scenario_workbook_rows(
        header_rows=[
            {
                "source_row_id": "scenario-header-row-3",
                "scenario_id": "SCN-MISSING-RULE",
                "scenario_name": "Missing Rule",
                "scenario_source": "USER_AUTHORED",
                "scope": "WHOLE_FACTORY",
            }
        ],
        rule_rows=[],
        equipment_override_rows=[],
        priority_override_rows=[],
        recipe_override_rows=[],
        output_request_rows=[],
        engine_version="planning-core-test-v1",
    )

    assert result.scenario_definitions == ()
    assert len(result.errors) == 1
    assert result.errors[0].source_row_id == "scenario-header-row-3"
    assert result.errors[0].field == "priority_rule"
    assert "SCN-MISSING-RULE" in result.errors[0].message


def test_ai_drafted_scenarios_are_normalized_as_non_executable_drafts():
    result = import_scenario_workbook_rows(
        header_rows=[
            {
                "source_row_id": "scenario-header-row-4",
                "scenario_id": "SCN-AI-DRAFT",
                "scenario_name": "AI Draft",
                "scenario_source": "AI_DRAFT",
                "scope": "HYDRAULIC",
                "domain_filters": "HYDRAULIC",
            }
        ],
        rule_rows=[
            {
                "scenario_id": "SCN-AI-DRAFT",
                "priority_rule": "SHORTEST_LEAD_TIME_PROXY",
            }
        ],
        equipment_override_rows=[],
        priority_override_rows=[],
        recipe_override_rows=[],
        output_request_rows=[],
        engine_version="planning-core-test-v1",
    )

    assert result.errors == ()
    scenario = result.scenario_definitions[0]
    assert scenario.scenario_source == "AI_DRAFT"
    assert scenario.is_executable is False


def test_built_in_scenario_templates_cover_first_mvp_priority_rules():
    templates = built_in_scenario_templates(engine_version="planning-core-test-v1")

    assert {
        template.priority_rule
        for template in templates
    } == {
        "SHORTEST_LEAD_TIME_PROXY",
        "HEAVY_WEIGHT_FIRST",
        "CUSTOMER_PRIORITY",
        "EQUIPMENT_UNAVAILABLE",
        "BOTTLENECK_AVOIDANCE",
    }
    assert {template.scenario_source for template in templates} == {"BUILT_IN"}
    assert all(template.is_executable for template in templates)
    assert all(template.engine_version == "planning-core-test-v1" for template in templates)


def test_scenario_comparison_is_deterministic_and_exposes_report_signals():
    scenarios = (
        _scenario("SCN-BASE"),
        _scenario("SCN-RISKY", priority_rule="BOTTLENECK_AVOIDANCE"),
        ScenarioDefinition(
            **{
                **_scenario("SCN-AI-DRAFT").__dict__,
                "scenario_source": "AI_DRAFT",
                "is_executable": False,
            }
        ),
    )
    reports_by_scenario_id = {
        "SCN-BASE": _report(
            missing=0,
            ambiguous=0,
            unplannable=0,
            risk_score=10,
            risk_signals=("PROXY_LOAD",),
        ),
        "SCN-RISKY": _report(
            missing=1,
            ambiguous=1,
            unplannable=2,
            risk_score=30,
            risk_signals=("PROXY_LOAD", "SNAPSHOT_UNAVAILABLE"),
        ),
    }

    first = compare_scenario_reports(
        scenarios=scenarios,
        reports_by_scenario_id=reports_by_scenario_id,
        engine_version="planning-core-test-v1",
    )
    second = compare_scenario_reports(
        scenarios=scenarios,
        reports_by_scenario_id=reports_by_scenario_id,
        engine_version="planning-core-test-v1",
    )

    assert first == second
    assert first.engine_version == "planning-core-test-v1"
    assert [row.scenario_id for row in first.rows] == ["SCN-BASE", "SCN-RISKY"]
    assert [row.rank for row in first.rows] == [1, 2]
    assert first.skipped_scenario_ids == ("SCN-AI-DRAFT",)

    baseline = first.rows[0]
    assert baseline.deterministic_metrics == {
        "ambiguous_recipe_count": 0,
        "missing_recipe_count": 0,
        "risk_score_total": 10,
        "unplannable_line_count": 0,
    }
    assert baseline.missing_recipe_count == 0
    assert baseline.ambiguous_recipe_count == 0
    assert baseline.unplannable_line_count == 0
    assert baseline.load_summary_rows == reports_by_scenario_id["SCN-BASE"].load_summary_rows
    assert baseline.bottleneck_risk_signals == ("PROXY_LOAD",)
    assert baseline.ranking_reasons == ("LOWEST_DETERMINISTIC_PROXY_SCORE",)
    assert baseline.ai_explanation == ""

    risky = first.rows[1]
    assert risky.missing_recipe_count == 1
    assert risky.ambiguous_recipe_count == 1
    assert risky.unplannable_line_count == 2
    assert risky.bottleneck_risk_signals == (
        "PROXY_LOAD",
        "SNAPSHOT_UNAVAILABLE",
    )


def _scenario(scenario_id, priority_rule="SHORTEST_LEAD_TIME_PROXY"):
    return ScenarioDefinition(
        scenario_id=scenario_id,
        scenario_name=scenario_id,
        scenario_source="USER_AUTHORED",
        scope="WHOLE_FACTORY",
        included_plan_batch_ids=("PLAN-TEST",),
        domain_filters=(),
        priority_rule=priority_rule,
        proxy_weights={},
        equipment_overrides={},
        priority_overrides={},
        recipe_overrides={},
        output_requirements=("LOAD_SUMMARY", "BOTTLENECK_RISK_REPORT"),
        engine_version="planning-core-test-v1",
        is_executable=True,
        source_row_id=f"{scenario_id}-row",
        raw_values={},
    )


def _report(*, missing, ambiguous, unplannable, risk_score, risk_signals):
    load_summary_rows = (
        LoadSummaryRow(
            domain_code="HYDRAULIC",
            process_group="CUTTING",
            equipment_group="HYD-CUT-01",
            recipe_id="R-HYD-100",
            recipe_step_no=10,
            plan_source_row_ids=("plan-row-1",),
            order_quantity_total=10,
            weight_total=100,
            proxy_load_units=10,
        ),
    )
    return LoadAndRiskReport(
        proxy_label="SHORTEST_LEAD_TIME_PROXY",
        timing_basis="NO_STANDARD_TIMES",
        is_precise_lead_time=False,
        load_summary_rows=load_summary_rows,
        load_totals=(LoadTotalRow("WHOLE_FACTORY", "ALL", 10),),
        bottleneck_risks=(
            BottleneckRiskRow(
                domain_code="HYDRAULIC",
                process_group="CUTTING",
                equipment_group="HYD-CUT-01",
                proxy_load_units=10,
                risk_level="HIGH" if "SNAPSHOT_UNAVAILABLE" in risk_signals else "LOW",
                risk_score=risk_score,
                signals=risk_signals,
            ),
        ),
        missing_recipe_count=missing,
        ambiguous_recipe_count=ambiguous,
        unplannable_line_count=unplannable,
    )
