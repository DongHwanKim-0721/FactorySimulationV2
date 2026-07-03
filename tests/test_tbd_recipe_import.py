import json
from pathlib import Path

from engine.planning_core import import_tbd_recipe_rows


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "planning_core" / "tbd_recipe_import"


def test_tbd_recipe_rows_normalize_headers_and_steps_into_recipe_contract():
    result = import_tbd_recipe_rows(
        _read_fixture_rows("header_rows.json"),
        _read_fixture_rows("step_rows.json"),
        import_batch_id="TBD-2026-07",
    )

    assert result.errors == ()
    assert len(result.recipe_headers) == 1
    assert len(result.recipe_steps) == 2

    header = result.recipe_headers[0]
    assert header.domain_code == "SHAPED_MATERIAL"
    assert header.recipe_id == "TBD-SHP-300"
    assert header.recipe_version == "1"
    assert header.recipe_status == "TBD"
    assert header.product_group == "PROFILE"
    assert header.item_code == "SHP-300"
    assert header.item_name == "Shaped profile C"
    assert header.representative_spec == "300C"
    assert header.first_input_material == "AL6061"
    assert header.source_type == "EXCEL_TBD"
    assert header.source_import_batch_id == "TBD-2026-07"
    assert header.confidence == "NEEDS_REVIEW"
    assert header.notes == "planner draft"
    assert header.source_row_id == "tbd-header-row-2"
    assert header.raw_values[" item_code "] == "SHP-300"

    first_step = result.recipe_steps[0]
    assert first_step.domain_code == "SHAPED_MATERIAL"
    assert first_step.recipe_id == "TBD-SHP-300"
    assert first_step.recipe_version == "1"
    assert first_step.step_no == 10
    assert first_step.process_group == "FORMING"
    assert first_step.process_name == "Form"
    assert first_step.process_code == "FRM"
    assert first_step.repeat_count == 2
    assert first_step.preferred_equipment == "SHP-FRM-01"
    assert first_step.alternate_equipment_names == ("SHP-FRM-02", "SHP-FRM-03")
    assert first_step.input_basis == "EA"
    assert first_step.quantity_factor == 1
    assert first_step.weight_factor == 0
    assert first_step.source_row_id == "tbd-step-row-2"
    assert first_step.raw_values["alternate_equipment_names"] == "SHP-FRM-02; SHP-FRM-03"


def _read_fixture_rows(name):
    return json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
