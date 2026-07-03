from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any, Mapping

from .contracts import RecipeHeader, RecipeStep, WorkOrderOperation
from .domains import normalize_domain_code


@dataclass(frozen=True)
class WorkOrderValidationError:
    source_row_id: str
    field: str
    message: str
    raw_values: dict[str, Any]


@dataclass(frozen=True)
class WorkOrderImportResult:
    operations: tuple[WorkOrderOperation, ...]
    errors: tuple[WorkOrderValidationError, ...]


@dataclass(frozen=True)
class RecipeCandidateExtractionResult:
    recipe_headers: tuple[RecipeHeader, ...]
    recipe_steps: tuple[RecipeStep, ...]


@dataclass(frozen=True)
class _RowValidationError(Exception):
    field: str
    message: str


HEADER_ALIASES = {
    "operation_date": "operation_date",
    "date": "operation_date",
    "작업일": "operation_date",
    "domain": "domain",
    "domain_code": "domain",
    "domain_label": "domain",
    "domain_source": "domain",
    "work_center": "domain",
    "작업장": "domain",
    "shift_or_team": "shift_or_team",
    "shift": "shift_or_team",
    "team": "shift_or_team",
    "조": "shift_or_team",
    "work_order_no": "work_order_no",
    "work_order": "work_order_no",
    "작업지시번호": "work_order_no",
    "process_sequence": "process_sequence",
    "공정순서": "process_sequence",
    "process_group": "process_group",
    "공정그룹": "process_group",
    "process_name": "process_name",
    "공정명": "process_name",
    "operation_sequence": "operation_sequence",
    "작업순서": "operation_sequence",
    "equipment_name": "equipment_name",
    "설비명": "equipment_name",
    "item_code": "item_code",
    "품목코드": "item_code",
    "item_name": "item_name",
    "품목명": "item_name",
    "instruction_quantity": "instruction_quantity",
    "지시수량": "instruction_quantity",
    "input_quantity": "input_quantity",
    "투입수량": "input_quantity",
    "output_quantity": "output_quantity",
    "생산수량": "output_quantity",
    "defect_quantity": "defect_quantity",
    "불량수량": "defect_quantity",
    "unit": "unit",
    "단위": "unit",
    "first_input_material": "first_input_material",
    "최초투입재": "first_input_material",
}


def import_work_order_operation_rows(
    rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    *,
    import_batch_id: str,
) -> WorkOrderImportResult:
    operations: list[WorkOrderOperation] = []
    errors: list[WorkOrderValidationError] = []

    for index, row in enumerate(rows, start=2):
        raw_values = dict(row)
        source_row_id = str(raw_values.get("source_row_id") or f"row-{index}")
        normalized = _normalize_headers(row)

        try:
            operation = WorkOrderOperation(
                import_batch_id=str(import_batch_id),
                operation_date=str(normalized.get("operation_date") or ""),
                domain_code=_normalize_domain_code(_required_text(normalized, "domain")),
                shift_or_team=str(normalized.get("shift_or_team") or ""),
                work_order_no=_required_text(normalized, "work_order_no"),
                process_sequence=_required_int(normalized, "process_sequence"),
                process_group=_required_text(normalized, "process_group"),
                process_name=_required_text(normalized, "process_name"),
                operation_sequence=_required_int(normalized, "operation_sequence"),
                equipment_name=str(normalized.get("equipment_name") or ""),
                item_code=_required_text(normalized, "item_code"),
                item_name=str(normalized.get("item_name") or ""),
                instruction_quantity=_optional_float(
                    normalized.get("instruction_quantity"),
                    "instruction_quantity",
                ),
                input_quantity=_optional_float(
                    normalized.get("input_quantity"),
                    "input_quantity",
                ),
                output_quantity=_optional_float(
                    normalized.get("output_quantity"),
                    "output_quantity",
                ),
                defect_quantity=_optional_float(
                    normalized.get("defect_quantity"),
                    "defect_quantity",
                ),
                unit=str(normalized.get("unit") or ""),
                first_input_material=str(normalized.get("first_input_material") or ""),
                source_row_id=source_row_id,
                raw_values=raw_values,
            )
        except _RowValidationError as exc:
            errors.append(
                WorkOrderValidationError(
                    source_row_id=source_row_id,
                    field=exc.field,
                    message=exc.message,
                    raw_values=raw_values,
                )
            )
            continue

        operations.append(operation)

    return WorkOrderImportResult(operations=tuple(operations), errors=tuple(errors))


def extract_recipe_candidates(
    operations: tuple[WorkOrderOperation, ...] | list[WorkOrderOperation],
) -> RecipeCandidateExtractionResult:
    groups: dict[tuple[str, str], list[WorkOrderOperation]] = {}
    for operation in operations:
        groups.setdefault((operation.domain_code, operation.item_code), []).append(operation)

    headers: list[RecipeHeader] = []
    steps: list[RecipeStep] = []

    for (domain_code, item_code), group in sorted(groups.items()):
        ordered_group = sorted(
            group,
            key=lambda operation: (
                operation.work_order_no,
                operation.process_sequence,
                operation.operation_sequence,
                operation.source_row_id,
            ),
        )
        first_operation = ordered_group[0]
        work_order_refs = tuple(
            sorted({operation.work_order_no for operation in ordered_group})
        )
        import_batch_ids = sorted(
            {operation.import_batch_id for operation in ordered_group}
        )
        recipe_id = _recipe_id(domain_code, item_code)
        headers.append(
            RecipeHeader(
                domain_code=domain_code,
                recipe_id=recipe_id,
                recipe_version="1",
                recipe_status="AUTO_CANDIDATE",
                product_group="",
                item_code=item_code,
                item_name=first_operation.item_name,
                representative_spec="",
                first_input_material=first_operation.first_input_material,
                source_type="HISTORICAL_WO",
                source_import_batch_id=",".join(import_batch_ids),
                source_work_order_refs=work_order_refs,
                usage_count=len(work_order_refs),
                confidence=(
                    "OBSERVED_SINGLE"
                    if len(work_order_refs) == 1
                    else "OBSERVED_MULTIPLE"
                ),
                last_observed_date=max(
                    (
                        operation.operation_date
                        for operation in ordered_group
                        if operation.operation_date
                    ),
                    default="",
                ),
                effective_from="",
                effective_to="",
                confirmed_by="",
                confirmed_at="",
                notes="candidate from historical work orders",
                source_row_id=first_operation.source_row_id,
                raw_values={},
            )
        )

        representative_route = [
            operation
            for operation in ordered_group
            if operation.work_order_no == work_order_refs[0]
        ]
        for operation in sorted(
            representative_route,
            key=lambda item: (
                item.process_sequence,
                item.operation_sequence,
                item.source_row_id,
            ),
        ):
            steps.append(
                RecipeStep(
                    domain_code=domain_code,
                    recipe_id=recipe_id,
                    recipe_version="1",
                    step_no=operation.process_sequence,
                    process_group=operation.process_group,
                    process_name=operation.process_name,
                    process_code="",
                    is_required=True,
                    repeat_count=1,
                    preferred_equipment=operation.equipment_name,
                    alternate_equipment_names=(),
                    input_basis=operation.unit,
                    quantity_factor=1,
                    weight_factor=0,
                    constraints={},
                    notes="standard time not available in historical import slice",
                    source_row_id=operation.source_row_id,
                    raw_values=operation.raw_values,
                )
            )

    return RecipeCandidateExtractionResult(
        recipe_headers=tuple(headers),
        recipe_steps=tuple(steps),
    )


def _normalize_headers(row: Mapping[str, Any]) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for header, value in row.items():
        canonical = HEADER_ALIASES.get(str(header).strip())
        if canonical is not None:
            normalized[canonical] = value
    return normalized


def _required_text(row: Mapping[str, Any], field: str) -> str:
    value = row.get(field)
    if value is None or str(value).strip() == "":
        raise _RowValidationError(field, f"Missing required work-order field: {field}")
    return str(value).strip()


def _required_int(row: Mapping[str, Any], field: str) -> int:
    value = _required_text(row, field)
    try:
        return int(value)
    except ValueError as exc:
        raise _RowValidationError(
            field,
            f"Invalid integer work-order field {field}: {value}",
        ) from exc


def _optional_float(value: Any, field: str) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise _RowValidationError(
            field,
            f"Invalid numeric work-order field {field}: {value}",
        ) from exc


def _normalize_domain_code(value: str) -> str:
    try:
        return normalize_domain_code(value)
    except ValueError as exc:
        raise _RowValidationError("domain", str(exc)) from exc


def _recipe_id(domain_code: str, item_code: str) -> str:
    safe_item_code = re.sub(r"[^A-Z0-9]+", "-", item_code.upper()).strip("-")
    return f"AUTO-{domain_code}-{safe_item_code}"
