from pathlib import Path

from engine.operator_library import (
    delete_operator_template,
    load_operator_templates,
    save_operator_templates,
    upsert_operator_template,
)


def test_missing_operator_library_loads_as_empty():
    path = Path("tests/.tmp_missing_operator_library.json")
    path.unlink(missing_ok=True)

    assert load_operator_templates(path) == []


def test_operator_library_save_load_roundtrip():
    path = Path("tests/.tmp_operator_library.json")
    templates = []

    try:
        template, created = upsert_operator_template(
            templates,
            "Operator A",
            {"CUTTING", "HEAT"},
        )
        save_operator_templates(templates, path)
        loaded = load_operator_templates(path)

        assert created is True
        assert template.id == 1
        assert loaded[0].name == "Operator A"
        assert loaded[0].qualified_process_types == {"CUTTING", "HEAT"}
    finally:
        path.unlink(missing_ok=True)


def test_operator_library_upsert_updates_same_name_without_duplicate():
    templates = []

    first, first_created = upsert_operator_template(templates, "Operator A", {"CUTTING"})
    second, second_created = upsert_operator_template(templates, "operator a", {"HEAT"})

    assert first_created is True
    assert second_created is False
    assert first.id == second.id
    assert len(templates) == 1
    assert templates[0].name == "operator a"
    assert templates[0].qualified_process_types == {"HEAT"}


def test_operator_library_delete_removes_template():
    templates = []
    template, _created = upsert_operator_template(templates, "Operator A", {"CUTTING"})

    deleted = delete_operator_template(templates, template.id)

    assert deleted == template
    assert templates == []
    assert delete_operator_template(templates, template.id) is None
