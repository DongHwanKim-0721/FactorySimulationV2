import json
from pathlib import Path
from typing import Any, Mapping
from xml.sax.saxutils import escape
from zipfile import ZIP_DEFLATED, ZipFile

from engine.planning_core import PLANNING_WORKBOOK_SHEETS


FIXTURE_DIR = Path(__file__).parent / "fixtures" / "planning_core" / "e2e"
ENGINE_VERSION = "planning-core-e2e-v1"

SHEET_FIXTURE_FILES = {
    PLANNING_WORKBOOK_SHEETS["production_plan_rows"]: "production_plan_rows.json",
    PLANNING_WORKBOOK_SHEETS["work_order_rows"]: "work_order_rows.json",
    PLANNING_WORKBOOK_SHEETS["equipment_rows"]: "equipment_rows.json",
    PLANNING_WORKBOOK_SHEETS["tbd_recipe_header_rows"]: "tbd_recipe_header_rows.json",
    PLANNING_WORKBOOK_SHEETS["tbd_recipe_step_rows"]: "tbd_recipe_step_rows.json",
    PLANNING_WORKBOOK_SHEETS["scenario_header_rows"]: "scenario_header_rows.json",
    PLANNING_WORKBOOK_SHEETS["scenario_rule_rows"]: "scenario_rule_rows.json",
    PLANNING_WORKBOOK_SHEETS[
        "scenario_equipment_override_rows"
    ]: "scenario_equipment_override_rows.json",
    PLANNING_WORKBOOK_SHEETS[
        "scenario_priority_override_rows"
    ]: "scenario_priority_override_rows.json",
    PLANNING_WORKBOOK_SHEETS[
        "scenario_recipe_override_rows"
    ]: "scenario_recipe_override_rows.json",
    PLANNING_WORKBOOK_SHEETS[
        "scenario_output_request_rows"
    ]: "scenario_output_request_rows.json",
}

EMPTY_SHEET_HEADERS = {
    PLANNING_WORKBOOK_SHEETS["scenario_recipe_override_rows"]: [
        "source_row_id",
        "scenario_id",
        "domain",
        "item_code",
        "recipe_id",
    ],
}


def write_e2e_planning_workbook(workbook_path: Path) -> None:
    sheets: dict[str, tuple[list[str], list[Mapping[str, Any]]]] = {}
    for sheet_name, fixture_file in SHEET_FIXTURE_FILES.items():
        rows = _rows(fixture_file)
        sheets[sheet_name] = (_headers_for(sheet_name, rows), rows)

    _write_minimal_xlsx(workbook_path, sheets)


def _rows(file_name: str) -> list[Mapping[str, Any]]:
    return json.loads((FIXTURE_DIR / file_name).read_text(encoding="utf-8"))


def _headers_for(sheet_name: str, rows: list[Mapping[str, Any]]) -> list[str]:
    if not rows:
        return EMPTY_SHEET_HEADERS[sheet_name]

    headers = list(rows[0].keys())
    for row in rows[1:]:
        for key in row:
            if key not in headers:
                headers.append(key)
    return headers


def _write_minimal_xlsx(
    workbook_path: Path,
    sheets: Mapping[str, tuple[list[str], list[Mapping[str, Any]]]],
) -> None:
    sheet_names = list(sheets.keys())
    with ZipFile(workbook_path, "w", ZIP_DEFLATED) as archive:
        archive.writestr("[Content_Types].xml", _content_types_xml(len(sheet_names)))
        archive.writestr("_rels/.rels", _root_rels_xml())
        archive.writestr("xl/workbook.xml", _workbook_xml(sheet_names))
        archive.writestr("xl/_rels/workbook.xml.rels", _workbook_rels_xml(sheet_names))

        for sheet_index, sheet_name in enumerate(sheet_names, start=1):
            headers, rows = sheets[sheet_name]
            archive.writestr(
                f"xl/worksheets/sheet{sheet_index}.xml",
                _worksheet_xml(headers, rows),
            )


def _content_types_xml(sheet_count: int) -> str:
    overrides = "".join(
        (
            f'<Override PartName="/xl/worksheets/sheet{index}.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.'
            'spreadsheetml.worksheet+xml"/>'
        )
        for index in range(1, sheet_count + 1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
        '<Default Extension="rels" '
        'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
        '<Default Extension="xml" ContentType="application/xml"/>'
        '<Override PartName="/xl/workbook.xml" '
        'ContentType="application/vnd.openxmlformats-officedocument.'
        'spreadsheetml.sheet.main+xml"/>'
        f"{overrides}"
        "</Types>"
    )


def _root_rels_xml() -> str:
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        '<Relationship Id="rId1" '
        'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
        'Target="xl/workbook.xml"/>'
        "</Relationships>"
    )


def _workbook_xml(sheet_names: list[str]) -> str:
    sheets_xml = "".join(
        (
            f'<sheet name="{_xml_attr(sheet_name)}" sheetId="{index}" '
            f'r:id="rId{index}"/>'
        )
        for index, sheet_name in enumerate(sheet_names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        f"<sheets>{sheets_xml}</sheets>"
        "</workbook>"
    )


def _workbook_rels_xml(sheet_names: list[str]) -> str:
    relationships = "".join(
        (
            f'<Relationship Id="rId{index}" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
            f'Target="worksheets/sheet{index}.xml"/>'
        )
        for index, _ in enumerate(sheet_names, start=1)
    )
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        f"{relationships}"
        "</Relationships>"
    )


def _worksheet_xml(
    headers: list[str],
    rows: list[Mapping[str, Any]],
) -> str:
    row_xml = [_row_xml(1, headers)]
    for row_index, row in enumerate(rows, start=2):
        row_xml.append(_row_xml(row_index, [row.get(header, "") for header in headers]))
    return (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
        f"<sheetData>{''.join(row_xml)}</sheetData>"
        "</worksheet>"
    )


def _row_xml(row_index: int, values: list[Any]) -> str:
    cells = "".join(
        _cell_xml(row_index, column_index, value)
        for column_index, value in enumerate(values, start=1)
    )
    return f'<row r="{row_index}">{cells}</row>'


def _cell_xml(row_index: int, column_index: int, value: Any) -> str:
    reference = f"{_column_name(column_index)}{row_index}"
    return (
        f'<c r="{reference}" t="inlineStr">'
        f"<is><t>{_xml_text(value)}</t></is>"
        "</c>"
    )


def _column_name(column_index: int) -> str:
    name = ""
    while column_index:
        column_index, remainder = divmod(column_index - 1, 26)
        name = chr(ord("A") + remainder) + name
    return name


def _xml_text(value: Any) -> str:
    return escape("" if value is None else str(value))


def _xml_attr(value: Any) -> str:
    return escape(str(value), {'"': "&quot;"})
