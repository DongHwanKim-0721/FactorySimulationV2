from engine.planning_core import (
    ProductionPlanLine,
    RecipeHeader,
    match_plan_lines_to_recipes,
)


def test_plan_lines_match_only_recipes_in_the_same_planning_domain():
    plan_lines = (
        _plan_line("HYDRAULIC", "COMMON-1", "hyd-plan-row"),
        _plan_line("STS", "COMMON-1", "sts-plan-row"),
    )
    recipe_headers = (
        _recipe_header("HYDRAULIC", "COMMON-1", "R-HYD-COMMON", "AUTO_CANDIDATE"),
    )

    result = match_plan_lines_to_recipes(plan_lines, recipe_headers)

    assert [match.status for match in result.matches] == ["MATCHED", "MISSING"]
    assert result.matches[0].selected_recipe_id == "R-HYD-COMMON"
    assert result.matches[0].candidate_recipe_ids == ("R-HYD-COMMON",)
    assert result.matches[1].selected_recipe_id == ""
    assert result.matches[1].candidate_recipe_ids == ()
    assert result.matches[1].plan_source_row_id == "sts-plan-row"
    assert result.tbd_report_rows[0].plan_source_row_id == "sts-plan-row"
    assert result.tbd_report_rows[0].domain_code == "STS"
    assert result.tbd_report_rows[0].item_code == "COMMON-1"
    assert result.tbd_report_rows[0].reason == "MISSING"


def test_multiple_same_domain_candidates_are_ambiguous_without_auto_selection():
    plan_lines = (_plan_line("HYDRAULIC", "HYD-100", "hyd-plan-row"),)
    recipe_headers = (
        _recipe_header("HYDRAULIC", "HYD-100", "R-HYD-100-A", "AUTO_CANDIDATE"),
        _recipe_header("HYDRAULIC", "HYD-100", "R-HYD-100-B", "USER_CONFIRMED"),
    )

    result = match_plan_lines_to_recipes(plan_lines, recipe_headers)

    match = result.matches[0]
    assert match.status == "AMBIGUOUS"
    assert match.selected_recipe_id == ""
    assert match.candidate_recipe_ids == ("R-HYD-100-A", "R-HYD-100-B")
    assert result.tbd_report_rows == ()


def test_recipe_override_selects_a_scenario_recipe_candidate():
    plan_lines = (_plan_line("HYDRAULIC", "HYD-100", "hyd-plan-row"),)
    recipe_headers = (
        _recipe_header("HYDRAULIC", "HYD-100", "R-HYD-100-A", "AUTO_CANDIDATE"),
        _recipe_header("HYDRAULIC", "HYD-100", "R-HYD-100-B", "USER_CONFIRMED"),
    )

    result = match_plan_lines_to_recipes(
        plan_lines,
        recipe_headers,
        recipe_overrides={("HYDRAULIC", "HYD-100"): "R-HYD-100-B"},
    )

    match = result.matches[0]
    assert match.status == "MATCHED"
    assert match.selected_recipe_id == "R-HYD-100-B"
    assert match.candidate_recipe_ids == ("R-HYD-100-A", "R-HYD-100-B")
    assert match.reason == "SCENARIO_RECIPE_OVERRIDE"
    assert result.tbd_report_rows == ()


def test_recipe_override_can_select_a_tbd_recipe_for_scenario_reporting():
    plan_lines = (_plan_line("SHAPED_MATERIAL", "SHP-300", "shp-plan-row"),)
    recipe_headers = (
        _recipe_header("SHAPED_MATERIAL", "SHP-300", "TBD-SHP-300", "TBD"),
    )

    result = match_plan_lines_to_recipes(
        plan_lines,
        recipe_headers,
        recipe_overrides={("SHAPED_MATERIAL", "SHP-300"): "TBD-SHP-300"},
    )

    match = result.matches[0]
    assert match.status == "MATCHED"
    assert match.selected_recipe_id == "TBD-SHP-300"
    assert match.candidate_recipe_ids == ("TBD-SHP-300",)
    assert match.tbd_recipe_ids == ("TBD-SHP-300",)
    assert match.reason == "SCENARIO_RECIPE_OVERRIDE"
    assert result.tbd_report_rows == ()


def test_recipe_override_does_not_select_deprecated_recipe():
    plan_lines = (_plan_line("STS", "STS-200", "sts-plan-row"),)
    recipe_headers = (
        _recipe_header("STS", "STS-200", "R-STS-OLD", "DEPRECATED"),
    )

    result = match_plan_lines_to_recipes(
        plan_lines,
        recipe_headers,
        recipe_overrides={("STS", "STS-200"): "R-STS-OLD"},
    )

    match = result.matches[0]
    assert match.status == "DEPRECATED_ONLY"
    assert match.selected_recipe_id == ""
    assert match.candidate_recipe_ids == ()
    assert match.deprecated_recipe_ids == ("R-STS-OLD",)
    assert match.reason == "OVERRIDE_RECIPE_DEPRECATED"
    assert result.tbd_report_rows[0].reason == "OVERRIDE_RECIPE_DEPRECATED"


def test_deprecated_recipes_are_reported_but_not_selected_by_default():
    plan_lines = (_plan_line("STS", "STS-200", "sts-plan-row"),)
    recipe_headers = (
        _recipe_header("STS", "STS-200", "R-STS-OLD", "DEPRECATED"),
    )

    result = match_plan_lines_to_recipes(plan_lines, recipe_headers)

    match = result.matches[0]
    assert match.status == "DEPRECATED_ONLY"
    assert match.selected_recipe_id == ""
    assert match.deprecated_recipe_ids == ("R-STS-OLD",)
    assert match.candidate_recipe_ids == ()
    assert result.tbd_report_rows[0].reason == "DEPRECATED_ONLY"


def _plan_line(domain_code, item_code, source_row_id):
    return ProductionPlanLine(
        plan_batch_id="PLAN-TEST",
        plan_period="2026-07",
        plan_type="MONTHLY",
        domain_code=domain_code,
        domain_label=domain_code,
        customer_name="customer",
        customer_order_ref="order-ref",
        order_type="normal",
        product_group="group",
        item_code=item_code,
        item_name=f"{item_code} item",
        order_quantity=1,
        weight=None,
        unit="EA",
        source_row_id=source_row_id,
        raw_values={},
    )


def _recipe_header(domain_code, item_code, recipe_id, recipe_status):
    return RecipeHeader(
        domain_code=domain_code,
        recipe_id=recipe_id,
        recipe_version="1",
        recipe_status=recipe_status,
        product_group="group",
        item_code=item_code,
        item_name=f"{item_code} item",
        representative_spec="",
        first_input_material="",
        source_type="TEST",
        source_import_batch_id="TEST",
        source_work_order_refs=(),
        usage_count=1,
        confidence="TEST",
        last_observed_date="",
        effective_from="",
        effective_to="",
        confirmed_by="",
        confirmed_at="",
        notes="",
        source_row_id=f"{recipe_id}-row",
        raw_values={},
    )
