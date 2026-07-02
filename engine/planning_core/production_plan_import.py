from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import ProductionPlanLine
from .domains import normalize_domain_code


@dataclass(frozen=True)
class ProductionPlanValidationError:
    source_row_id: str
    field: str
    message: str
    raw_values: dict[str, Any]


@dataclass(frozen=True)
class ProductionPlanImportResult:
    lines: tuple[ProductionPlanLine, ...]
    errors: tuple[ProductionPlanValidationError, ...]


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
    "작업장": "domain",
    "작업센터": "domain",
    "customer": "customer_name",
    "customer_name": "customer_name",
    "고객": "customer_name",
    "고객명": "customer_name",
    "customer_order_ref": "customer_order_ref",
    "order_ref": "customer_order_ref",
    "order_reference": "customer_order_ref",
    "고객주문참조": "customer_order_ref",
    "주문참조": "customer_order_ref",
    "order_type": "order_type",
    "주문유형": "order_type",
    "product_group": "product_group",
    "제품군": "product_group",
    "item_code": "item_code",
    "품목코드": "item_code",
    "item_name": "item_name",
    "품목명": "item_name",
    "order_quantity": "order_quantity",
    "quantity": "order_quantity",
    "qty": "order_quantity",
    "수량": "order_quantity",
    "계획수량": "order_quantity",
    "weight": "weight",
    "중량": "weight",
    "unit": "unit",
    "단위": "unit",
}


def import_production_plan_rows(
    rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    *,
    plan_batch_id: str,
    plan_period: str,
    plan_type: str,
) -> ProductionPlanImportResult:
    lines: list[ProductionPlanLine] = []
    errors: list[ProductionPlanValidationError] = []

    for index, row in enumerate(rows, start=2):
        raw_values = dict(row)
        source_row_id = str(raw_values.get("source_row_id") or f"row-{index}")
        normalized = _normalize_headers(row)

        try:
            domain_label = _required_text(normalized, "domain")
            domain_code = _normalize_domain_code(domain_label)
            line = ProductionPlanLine(
                plan_batch_id=str(plan_batch_id),
                plan_period=str(plan_period),
                plan_type=str(plan_type).upper(),
                domain_code=domain_code,
                domain_label=domain_label,
                customer_name=_required_text(normalized, "customer_name"),
                customer_order_ref=str(normalized.get("customer_order_ref") or ""),
                order_type=str(normalized.get("order_type") or ""),
                product_group=str(normalized.get("product_group") or ""),
                item_code=_required_text(normalized, "item_code"),
                item_name=_required_text(normalized, "item_name"),
                order_quantity=_required_float(normalized, "order_quantity"),
                weight=_optional_float(normalized.get("weight"), "weight"),
                unit=str(normalized.get("unit") or ""),
                source_row_id=source_row_id,
                raw_values=raw_values,
            )
        except _RowValidationError as exc:
            errors.append(
                ProductionPlanValidationError(
                    source_row_id=source_row_id,
                    field=exc.field,
                    message=exc.message,
                    raw_values=raw_values,
                )
            )
            continue

        lines.append(line)

    return ProductionPlanImportResult(lines=tuple(lines), errors=tuple(errors))


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
        raise _RowValidationError(
            field,
            f"Missing required production-plan field: {field}",
        )
    return str(value).strip()


def _required_float(row: Mapping[str, Any], field: str) -> float:
    value = _required_text(row, field)
    try:
        return float(value)
    except ValueError as exc:
        raise _RowValidationError(
            field,
            f"Invalid numeric production-plan field {field}: {value}",
        ) from exc


def _optional_float(value: Any, field: str) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(value)
    except ValueError as exc:
        raise _RowValidationError(
            field,
            f"Invalid numeric production-plan field {field}: {value}",
        ) from exc


def _normalize_domain_code(value: str) -> str:
    try:
        return normalize_domain_code(value)
    except ValueError as exc:
        raise _RowValidationError("domain", str(exc)) from exc
