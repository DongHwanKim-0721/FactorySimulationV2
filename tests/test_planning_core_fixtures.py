from pathlib import Path

from engine.planning_core import load_fixture_set, render_fixture_report_snapshot


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "planning_core" / "minimal"


def test_minimal_planning_fixture_preserves_domain_labels_and_codes():
    fixture_set = load_fixture_set(FIXTURE_DIR)

    assert {
        domain.domain_code: domain.domain_label
        for domain in fixture_set.domains
    } == {
        "HYDRAULIC": "유압",
        "STS": "STS",
        "SHAPED_MATERIAL": "이형재",
    }
    assert {
        domain.domain_code: domain.source_value
        for domain in fixture_set.domains
    } == {
        "HYDRAULIC": "유압",
        "STS": "STS",
        "SHAPED_MATERIAL": "이형재",
    }
    assert {
        domain.substitution_policy
        for domain in fixture_set.domains
    } == {"NO_CROSS_DOMAIN_SUBSTITUTION"}


def test_minimal_fixture_loads_core_contract_surfaces_with_source_traceability():
    fixture_set = load_fixture_set(FIXTURE_DIR)

    assert len(fixture_set.production_plan_lines) == 3
    assert len(fixture_set.work_order_operations) == 3
    assert len(fixture_set.equipment_snapshots) == 3
    assert len(fixture_set.recipe_headers) == 3
    assert len(fixture_set.recipe_steps) == 3
    assert len(fixture_set.scenario_definitions) == 2

    plan_line = fixture_set.production_plan_lines[0]
    assert plan_line.domain_code == "HYDRAULIC"
    assert plan_line.source_row_id == "plan-row-2"
    assert plan_line.raw_values["작업장"] == "유압"
    assert plan_line.raw_values["고객주문참조"] == "전화요청-7월-A"

    work_order = fixture_set.work_order_operations[0]
    assert work_order.domain_code == "HYDRAULIC"
    assert work_order.work_order_no == "WO-HYD-001"
    assert work_order.source_row_id == "wo-row-8"
    assert work_order.raw_values["작업장"] == "유압"

    equipment = fixture_set.equipment_snapshots[0]
    assert equipment.domain_code == "HYDRAULIC"
    assert equipment.equipment_id == "HYD-CUT-01"
    assert equipment.source_row_id == "eq-row-4"
    assert equipment.raw_values["상태"] == "가동"

    recipe_header = fixture_set.recipe_headers[0]
    assert recipe_header.domain_code == "HYDRAULIC"
    assert recipe_header.recipe_status == "AUTO_CANDIDATE"
    assert recipe_header.source_work_order_refs == ("WO-HYD-001",)

    recipe_step = fixture_set.recipe_steps[0]
    assert recipe_step.domain_code == "HYDRAULIC"
    assert recipe_step.step_no == 10
    assert recipe_step.source_row_id == "recipe-step-row-2"

    ai_draft = fixture_set.scenario_definitions[1]
    assert ai_draft.scenario_source == "AI_DRAFT"
    assert ai_draft.is_executable is False


def test_fixture_report_snapshot_is_deterministic_and_keeps_ai_advisory():
    fixture_set = load_fixture_set(FIXTURE_DIR)

    snapshot = render_fixture_report_snapshot(fixture_set)

    assert snapshot == render_fixture_report_snapshot(fixture_set)
    assert snapshot == (
        FIXTURE_DIR / "expected_report_snapshot.json"
    ).read_text(encoding="utf-8")
    assert "DETERMINISTIC_ENGINE" in snapshot
    assert "DRAFTS_AND_RECOMMENDATIONS_ONLY" in snapshot
    assert "DUE_DATE_SCHEDULING" in snapshot
    assert "STANDARD_TIME_CALCULATION" in snapshot
