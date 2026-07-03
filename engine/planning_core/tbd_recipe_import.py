from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import RecipeHeader, RecipeStep
from .domains import normalize_domain_code


@dataclass(frozen=True)
class TbdRecipeValidationError:
    source_row_id: str
    field: str
    message: str
    raw_values: dict[str, Any]


@dataclass(frozen=True)
class TbdRecipeImportResult:
    recipe_headers: tuple[RecipeHeader, ...]
    recipe_steps: tuple[RecipeStep, ...]
    errors: tuple[TbdRecipeValidationError, ...]


@dataclass(frozen=True)
class _RowValidationError(Exception):
    field: str
    message: str


HEADER_ALIASES = {
    "domain": "domain",
    "domain_code": "domain",
    "domain_label": "domain",
    "domain_source": "domain",
    "work_center": "domain",
    "recipe_id": "recipe_id",
    "recipe_version": "recipe_version",
    "product_group": "product_group",
    "item_code": "item_code",
    "item_name": "item_name",
    "representative_spec": "representative_spec",
    "first_input_material": "first_input_material",
    "source_work_order_refs": "source_work_order_refs",
    "last_observed_date": "last_observed_date",
    "notes": "notes",
}

STEP_ALIASES = {
    "domain": "domain",
    "domain_code": "domain",
    "domain_label": "domain",
    "domain_source": "domain",
    "work_center": "domain",
    "recipe_id": "recipe_id",
    "recipe_version": "recipe_version",
    "step_no": "step_no",
    "process_group": "process_group",
    "process_name": "process_name",
    "process_code": "process_code",
    "is_required": "is_required",
    "repeat_count": "repeat_count",
    "preferred_equipment": "preferred_equipment",
    "alternate_equipment_names": "alternate_equipment_names",
    "input_basis": "input_basis",
    "quantity_factor": "quantity_factor",
    "weight_factor": "weight_factor",
    "constraints": "constraints",
    "notes": "notes",
}


def import_tbd_recipe_rows(
    header_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    step_rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    *,
    import_batch_id: str,
) -> TbdRecipeImportResult:
    recipe_headers: list[RecipeHeader] = []
    recipe_steps: list[RecipeStep] = []
    errors: list[TbdRecipeValidationError] = []

    for index, row in enumerate(header_rows, start=2):
        raw_values = dict(row)
        source_row_id = str(raw_values.get("source_row_id") or f"header-row-{index}")
        normalized = _normalize_headers(row, HEADER_ALIASES)
        try:
            header = RecipeHeader(
                domain_code=_normalize_domain_code(_required_text(normalized, "domain")),
                recipe_id=_required_text(normalized, "recipe_id"),
                recipe_version=str(normalized.get("recipe_version") or "1"),
                recipe_status="TBD",
                product_group=str(normalized.get("product_group") or ""),
                item_code=_required_text(normalized, "item_code"),
                item_name=_required_text(normalized, "item_name"),
                representative_spec=str(normalized.get("representative_spec") or ""),
                first_input_material=str(normalized.get("first_input_material") or ""),
                source_type="EXCEL_TBD",
                source_import_batch_id=str(import_batch_id),
                source_work_order_refs=_parse_text_tuple(
                    normalized.get("source_work_order_refs")
                ),
                usage_count=0,
                confidence="NEEDS_REVIEW",
                last_observed_date=str(normalized.get("last_observed_date") or ""),
                effective_from="",
                effective_to="",
                confirmed_by="",
                confirmed_at="",
                notes=str(normalized.get("notes") or ""),
                source_row_id=source_row_id,
                raw_values=raw_values,
            )
        except _RowValidationError as exc:
            errors.append(_validation_error(source_row_id, exc, raw_values))
            continue
        recipe_headers.append(header)

    for index, row in enumerate(step_rows, start=2):
        raw_values = dict(row)
        source_row_id = str(raw_values.get("source_row_id") or f"step-row-{index}")
        normalized = _normalize_headers(row, STEP_ALIASES)
        try:
            step = RecipeStep(
                domain_code=_normalize_domain_code(_required_text(normalized, "domain")),
                recipe_id=_required_text(normalized, "recipe_id"),
                recipe_version=str(normalized.get("recipe_version") or "1"),
                step_no=_required_int(normalized, "step_no"),
                process_group=_required_text(normalized, "process_group"),
                process_name=_required_text(normalized, "process_name"),
                process_code=str(normalized.get("process_code") or ""),
                is_required=_optional_bool(normalized.get("is_required"), default=True),
                repeat_count=_optional_int(
                    normalized.get("repeat_count"),
                    "repeat_count",
                    default=1,
                ),
                preferred_equipment=str(normalized.get("preferred_equipment") or ""),
                alternate_equipment_names=_parse_text_tuple(
                    normalized.get("alternate_equipment_names")
                ),
                input_basis=str(normalized.get("input_basis") or ""),
                quantity_factor=_optional_float(
                    normalized.get("quantity_factor"),
                    "quantity_factor",
                    default=1,
                ),
                weight_factor=_optional_float(
                    normalized.get("weight_factor"),
                    "weight_factor",
                    default=0,
                ),
                constraints=_optional_dict(normalized.get("constraints"), "constraints"),
                notes=str(normalized.get("notes") or ""),
                source_row_id=source_row_id,
                raw_values=raw_values,
            )
        except _RowValidationError as exc:
            errors.append(_validation_error(source_row_id, exc, raw_values))
            continue
        recipe_steps.append(step)

    return TbdRecipeImportResult(
        recipe_headers=tuple(recipe_headers),
        recipe_steps=tuple(recipe_steps),
        errors=tuple(errors),
    )


def _normalize_headers(
    row: Mapping[str, Any],
    aliases: Mapping[str, str],
) -> dict[str, Any]:
    normalized: dict[str, Any] = {}
    for header, value in row.items():
        canonical = aliases.get(str(header).strip())
        if canonical is not None:
            normalized[canonical] = value
    return normalized


def _required_text(row: Mapping[str, Any], field: str) -> str:
    value = row.get(field)
    if value is None or str(value).strip() == "":
        raise _RowValidationError(
            field,
            f"Missing required T.B.D recipe field: {field}",
        )
    return str(value).strip()


def _required_int(row: Mapping[str, Any], field: str) -> int:
    value = _required_text(row, field)
    try:
        return int(value)
    except ValueError as exc:
        raise _RowValidationError(
            field,
            f"Invalid integer T.B.D recipe field {field}: {value}",
        ) from exc


def _optional_int(value: Any, field: str, *, default: int) -> int:
    if value is None or str(value).strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise _RowValidationError(
            field,
            f"Invalid integer T.B.D recipe field {field}: {value}",
        ) from exc


def _optional_float(value: Any, field: str, *, default: float) -> float:
    if value is None or str(value).strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise _RowValidationError(
            field,
            f"Invalid numeric T.B.D recipe field {field}: {value}",
        ) from exc


def _optional_bool(value: Any, *, default: bool) -> bool:
    if value is None or str(value).strip() == "":
        return default
    if isinstance(value, bool):
        return value
    normalized = str(value).strip().upper()
    if normalized in {"TRUE", "Y", "YES", "1"}:
        return True
    if normalized in {"FALSE", "N", "NO", "0"}:
        return False
    raise _RowValidationError("is_required", f"Invalid boolean T.B.D recipe field: {value}")


def _optional_dict(value: Any, field: str) -> dict[str, Any]:
    if value is None or value == "":
        return {}
    if isinstance(value, dict):
        return dict(value)
    raise _RowValidationError(field, f"T.B.D recipe field {field} must be a mapping.")


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


def _normalize_domain_code(value: str) -> str:
    try:
        return normalize_domain_code(value)
    except ValueError as exc:
        raise _RowValidationError("domain", str(exc)) from exc


def _validation_error(
    source_row_id: str,
    exc: _RowValidationError,
    raw_values: dict[str, Any],
) -> TbdRecipeValidationError:
    return TbdRecipeValidationError(
        source_row_id=source_row_id,
        field=exc.field,
        message=exc.message,
        raw_values=raw_values,
    )
