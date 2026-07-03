from engine.planning_core import (
    EquipmentSnapshot,
    ProductionPlanLine,
    RecipeHeader,
    RecipeStep,
    generate_load_and_risk_report,
    match_plan_lines_to_recipes,
)


def test_load_summary_expands_matched_recipe_steps_by_domain_and_whole_factory():
    plan_lines = (
        _plan_line("HYDRAULIC", "HYD-100", "hyd-plan-row", quantity=10, weight=100),
        _plan_line("STS", "STS-200", "sts-plan-row", quantity=5, weight=20),
    )
    matching_result = match_plan_lines_to_recipes(
        plan_lines,
        (
            _recipe_header("HYDRAULIC", "HYD-100", "R-HYD-100"),
            _recipe_header("STS", "STS-200", "R-STS-200"),
        ),
    )
    recipe_steps = (
        _recipe_step("HYDRAULIC", "R-HYD-100", 10, "CUTTING", "HYD-CUT-01"),
        _recipe_step(
            "HYDRAULIC",
            "R-HYD-100",
            20,
            "MACHINING",
            "HYD-MCH-01",
            repeat_count=2,
            quantity_factor=1.5,
        ),
        _recipe_step("STS", "R-STS-200", 10, "POLISHING", "STS-POL-01"),
    )

    report = generate_load_and_risk_report(
        plan_lines=plan_lines,
        matching_result=matching_result,
        recipe_steps=recipe_steps,
        equipment_snapshots=(),
    )

    assert report.proxy_label == "SHORTEST_LEAD_TIME_PROXY"
    assert report.timing_basis == "NO_STANDARD_TIMES"
    assert report.is_precise_lead_time is False
    assert report.missing_recipe_count == 0
    assert report.ambiguous_recipe_count == 0
    assert report.unplannable_line_count == 0
    assert [
        (
            row.domain_code,
            row.process_group,
            row.equipment_group,
            row.recipe_id,
            row.recipe_step_no,
            row.proxy_load_units,
        )
        for row in report.load_summary_rows
    ] == [
        ("HYDRAULIC", "CUTTING", "HYD-CUT-01", "R-HYD-100", 10, 10),
        ("HYDRAULIC", "MACHINING", "HYD-MCH-01", "R-HYD-100", 20, 30),
        ("STS", "POLISHING", "STS-POL-01", "R-STS-200", 10, 5),
    ]
    assert {
        (row.scope, row.domain_code, row.proxy_load_units)
        for row in report.load_totals
    } == {
        ("DOMAIN", "HYDRAULIC", 40),
        ("DOMAIN", "STS", 5),
        ("WHOLE_FACTORY", "ALL", 45),
    }


def test_bottleneck_risk_reflects_unavailable_snapshot_and_equipment_override():
    plan_lines = (
        _plan_line("HYDRAULIC", "HYD-100", "hyd-plan-row", quantity=10, weight=0),
        _plan_line("STS", "STS-200", "sts-plan-row", quantity=5, weight=0),
    )
    matching_result = match_plan_lines_to_recipes(
        plan_lines,
        (
            _recipe_header("HYDRAULIC", "HYD-100", "R-HYD-100"),
            _recipe_header("STS", "STS-200", "R-STS-200"),
        ),
    )
    recipe_steps = (
        _recipe_step("HYDRAULIC", "R-HYD-100", 10, "CUTTING", "HYD-CUT-01"),
        _recipe_step("STS", "R-STS-200", 10, "POLISHING", "STS-POL-01"),
    )

    report = generate_load_and_risk_report(
        plan_lines=plan_lines,
        matching_result=matching_result,
        recipe_steps=recipe_steps,
        equipment_snapshots=(
            _equipment_snapshot("HYDRAULIC", "CUTTING", "HYD-CUT-01", is_available=False),
            _equipment_snapshot("STS", "POLISHING", "STS-POL-01", is_available=True),
        ),
        equipment_overrides={"STS-POL-01": False},
    )

    risk_by_equipment = {
        risk.equipment_group: risk
        for risk in report.bottleneck_risks
    }
    assert risk_by_equipment["HYD-CUT-01"].risk_level == "HIGH"
    assert risk_by_equipment["HYD-CUT-01"].risk_score == 20
    assert risk_by_equipment["HYD-CUT-01"].signals == (
        "PROXY_LOAD",
        "SNAPSHOT_UNAVAILABLE",
    )
    assert risk_by_equipment["STS-POL-01"].risk_level == "HIGH"
    assert risk_by_equipment["STS-POL-01"].risk_score == 10
    assert risk_by_equipment["STS-POL-01"].signals == (
        "PROXY_LOAD",
        "OVERRIDE_UNAVAILABLE",
    )


def test_report_counts_missing_ambiguous_and_unplannable_lines():
    plan_lines = (
        _plan_line("HYDRAULIC", "HYD-100", "matched-row", quantity=10, weight=0),
        _plan_line("STS", "STS-MISSING", "missing-row", quantity=5, weight=0),
        _plan_line("STS", "STS-AMB", "ambiguous-row", quantity=5, weight=0),
    )
    matching_result = match_plan_lines_to_recipes(
        plan_lines,
        (
            _recipe_header("HYDRAULIC", "HYD-100", "R-HYD-100"),
            _recipe_header("STS", "STS-AMB", "R-STS-AMB-A"),
            _recipe_header("STS", "STS-AMB", "R-STS-AMB-B"),
        ),
    )

    report = generate_load_and_risk_report(
        plan_lines=plan_lines,
        matching_result=matching_result,
        recipe_steps=(
            _recipe_step("HYDRAULIC", "R-HYD-100", 10, "CUTTING", "HYD-CUT-01"),
        ),
        equipment_snapshots=(),
    )

    assert report.missing_recipe_count == 1
    assert report.ambiguous_recipe_count == 1
    assert report.unplannable_line_count == 2
    assert [row.plan_source_row_ids for row in report.load_summary_rows] == [
        ("matched-row",),
    ]


def test_load_summary_aggregates_multiple_plan_lines_for_the_same_recipe_step():
    plan_lines = (
        _plan_line("HYDRAULIC", "HYD-100", "plan-row-1", quantity=10, weight=100),
        _plan_line("HYDRAULIC", "HYD-100", "plan-row-2", quantity=5, weight=50),
    )
    matching_result = match_plan_lines_to_recipes(
        plan_lines,
        (_recipe_header("HYDRAULIC", "HYD-100", "R-HYD-100"),),
    )

    report = generate_load_and_risk_report(
        plan_lines=plan_lines,
        matching_result=matching_result,
        recipe_steps=(
            _recipe_step(
                "HYDRAULIC",
                "R-HYD-100",
                10,
                "CUTTING",
                "HYD-CUT-01",
                weight_factor=0.1,
            ),
        ),
        equipment_snapshots=(),
    )

    row = report.load_summary_rows[0]
    assert row.plan_source_row_ids == ("plan-row-1", "plan-row-2")
    assert row.order_quantity_total == 15
    assert row.weight_total == 150
    assert row.proxy_load_units == 30


def _plan_line(domain_code, item_code, source_row_id, *, quantity, weight):
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
        order_quantity=quantity,
        weight=weight,
        unit="EA",
        source_row_id=source_row_id,
        raw_values={},
    )


def _recipe_header(domain_code, item_code, recipe_id):
    return RecipeHeader(
        domain_code=domain_code,
        recipe_id=recipe_id,
        recipe_version="1",
        recipe_status="USER_CONFIRMED",
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


def _recipe_step(
    domain_code,
    recipe_id,
    step_no,
    process_group,
    preferred_equipment,
    *,
    repeat_count=1,
    quantity_factor=1,
    weight_factor=0,
):
    return RecipeStep(
        domain_code=domain_code,
        recipe_id=recipe_id,
        recipe_version="1",
        step_no=step_no,
        process_group=process_group,
        process_name=process_group.title(),
        process_code=process_group[:3],
        is_required=True,
        repeat_count=repeat_count,
        preferred_equipment=preferred_equipment,
        alternate_equipment_names=(),
        input_basis="EA",
        quantity_factor=quantity_factor,
        weight_factor=weight_factor,
        constraints={},
        notes="",
        source_row_id=f"{recipe_id}-{step_no}-row",
        raw_values={},
    )


def _equipment_snapshot(domain_code, process_group, equipment_id, *, is_available):
    return EquipmentSnapshot(
        snapshot_batch_id="EQ-TEST",
        snapshot_at="2026-07-01T08:00:00",
        domain_code=domain_code,
        process_group=process_group,
        equipment_id=equipment_id,
        equipment_name=equipment_id,
        equipment_status="AVAILABLE" if is_available else "DOWN",
        is_available=is_available,
        unavailable_reason="" if is_available else "maintenance",
        current_work_order_no="",
        current_process_sequence="",
        current_process_name="",
        current_item_code="",
        current_item_name="",
        elapsed_or_remaining_time="",
        source_row_id=f"{equipment_id}-row",
        raw_values={},
    )
