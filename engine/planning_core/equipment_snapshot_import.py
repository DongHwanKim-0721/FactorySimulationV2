from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from .contracts import EquipmentSnapshot
from .domains import normalize_domain_code


@dataclass(frozen=True)
class EquipmentSnapshotValidationError:
    source_row_id: str
    field: str
    message: str
    raw_values: dict[str, Any]


@dataclass(frozen=True)
class EquipmentSnapshotImportResult:
    snapshots: tuple[EquipmentSnapshot, ...]
    errors: tuple[EquipmentSnapshotValidationError, ...]


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
    "process_group": "process_group",
    "공정그룹": "process_group",
    "equipment_id": "equipment_id",
    "설비ID": "equipment_id",
    "equipment_name": "equipment_name",
    "설비명": "equipment_name",
    "equipment_status": "equipment_status",
    "status": "equipment_status",
    "상태": "equipment_status",
    "unavailable_reason": "unavailable_reason",
    "불가사유": "unavailable_reason",
    "notes": "unavailable_reason",
    "current_work_order_no": "current_work_order_no",
    "현재작업지시번호": "current_work_order_no",
    "current_process_sequence": "current_process_sequence",
    "현재공정순서": "current_process_sequence",
    "current_process_name": "current_process_name",
    "현재공정명": "current_process_name",
    "current_item_code": "current_item_code",
    "현재품목코드": "current_item_code",
    "current_item_name": "current_item_name",
    "현재품목명": "current_item_name",
    "elapsed_or_remaining_time": "elapsed_or_remaining_time",
    "경과또는잔여시간": "elapsed_or_remaining_time",
}

AVAILABLE_STATUS_VALUES = {
    "AVAILABLE",
    "RUNNING",
    "IDLE",
    "가동",
    "대기",
}

UNAVAILABLE_STATUS_VALUES = {
    "UNAVAILABLE",
    "DOWN",
    "STOPPED",
    "MAINTENANCE",
    "정비",
    "고장",
    "불가",
    "중지",
}


def import_equipment_snapshot_rows(
    rows: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...],
    *,
    snapshot_batch_id: str,
    snapshot_at: str,
) -> EquipmentSnapshotImportResult:
    snapshots: list[EquipmentSnapshot] = []
    errors: list[EquipmentSnapshotValidationError] = []

    for index, row in enumerate(rows, start=2):
        raw_values = dict(row)
        source_row_id = str(raw_values.get("source_row_id") or f"row-{index}")
        normalized = _normalize_headers(row)

        try:
            status = _required_text(normalized, "equipment_status")
            snapshot = EquipmentSnapshot(
                snapshot_batch_id=str(snapshot_batch_id),
                snapshot_at=str(snapshot_at),
                domain_code=_normalize_domain_code(_required_text(normalized, "domain")),
                process_group=_required_text(normalized, "process_group"),
                equipment_id=_required_text(normalized, "equipment_id"),
                equipment_name=_required_text(normalized, "equipment_name"),
                equipment_status=status,
                is_available=_normalize_availability(status),
                unavailable_reason=str(normalized.get("unavailable_reason") or ""),
                current_work_order_no=str(normalized.get("current_work_order_no") or ""),
                current_process_sequence=str(normalized.get("current_process_sequence") or ""),
                current_process_name=str(normalized.get("current_process_name") or ""),
                current_item_code=str(normalized.get("current_item_code") or ""),
                current_item_name=str(normalized.get("current_item_name") or ""),
                elapsed_or_remaining_time=str(normalized.get("elapsed_or_remaining_time") or ""),
                source_row_id=source_row_id,
                raw_values=raw_values,
            )
        except _RowValidationError as exc:
            errors.append(
                EquipmentSnapshotValidationError(
                    source_row_id=source_row_id,
                    field=exc.field,
                    message=exc.message,
                    raw_values=raw_values,
                )
            )
            continue

        snapshots.append(snapshot)

    return EquipmentSnapshotImportResult(
        snapshots=tuple(snapshots),
        errors=tuple(errors),
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
        raise _RowValidationError(
            field,
            f"Missing required equipment snapshot field: {field}",
        )
    return str(value).strip()


def _normalize_domain_code(value: str) -> str:
    try:
        return normalize_domain_code(value)
    except ValueError as exc:
        raise _RowValidationError("domain", str(exc)) from exc


def _normalize_availability(status: str) -> bool:
    normalized_status = status.strip().upper()
    if status in AVAILABLE_STATUS_VALUES or normalized_status in AVAILABLE_STATUS_VALUES:
        return True
    if status in UNAVAILABLE_STATUS_VALUES or normalized_status in UNAVAILABLE_STATUS_VALUES:
        return False
    raise _RowValidationError(
        "equipment_status",
        f"Unknown equipment availability status: {status}",
    )
