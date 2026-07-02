from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


NO_CROSS_DOMAIN_SUBSTITUTION = "NO_CROSS_DOMAIN_SUBSTITUTION"


@dataclass(frozen=True)
class PlanningDomain:
    domain_code: str
    domain_label: str
    substitution_policy: str = NO_CROSS_DOMAIN_SUBSTITUTION
    source_value: str = ""


@dataclass(frozen=True)
class ProductionPlanLine:
    plan_batch_id: str
    plan_period: str
    plan_type: str
    domain_code: str
    domain_label: str
    customer_name: str
    customer_order_ref: str
    order_type: str
    product_group: str
    item_code: str
    item_name: str
    order_quantity: float
    weight: float | None
    unit: str
    source_row_id: str
    raw_values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkOrderOperation:
    import_batch_id: str
    operation_date: str
    domain_code: str
    shift_or_team: str
    work_order_no: str
    process_sequence: int
    process_group: str
    process_name: str
    operation_sequence: int
    equipment_name: str
    item_code: str
    item_name: str
    instruction_quantity: float | None
    input_quantity: float | None
    output_quantity: float | None
    defect_quantity: float | None
    unit: str
    first_input_material: str
    source_row_id: str
    raw_values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class EquipmentSnapshot:
    snapshot_batch_id: str
    snapshot_at: str
    domain_code: str
    process_group: str
    equipment_id: str
    equipment_name: str
    equipment_status: str
    is_available: bool
    unavailable_reason: str
    current_work_order_no: str
    current_process_sequence: str
    current_process_name: str
    current_item_code: str
    current_item_name: str
    elapsed_or_remaining_time: str
    source_row_id: str
    raw_values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RecipeHeader:
    domain_code: str
    recipe_id: str
    recipe_version: str
    recipe_status: str
    product_group: str
    item_code: str
    item_name: str
    representative_spec: str
    first_input_material: str
    source_type: str
    source_import_batch_id: str
    source_work_order_refs: tuple[str, ...]
    usage_count: int
    confidence: str
    last_observed_date: str
    effective_from: str
    effective_to: str
    confirmed_by: str
    confirmed_at: str
    notes: str
    source_row_id: str
    raw_values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RecipeStep:
    domain_code: str
    recipe_id: str
    recipe_version: str
    step_no: int
    process_group: str
    process_name: str
    process_code: str
    is_required: bool
    repeat_count: int
    preferred_equipment: str
    alternate_equipment_names: tuple[str, ...]
    input_basis: str
    quantity_factor: float
    weight_factor: float
    constraints: dict[str, Any] = field(default_factory=dict)
    notes: str = ""
    source_row_id: str = ""
    raw_values: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ScenarioDefinition:
    scenario_id: str
    scenario_name: str
    scenario_source: str
    scope: str
    included_plan_batch_ids: tuple[str, ...]
    domain_filters: tuple[str, ...]
    priority_rule: str
    proxy_weights: dict[str, float]
    equipment_overrides: dict[str, Any]
    priority_overrides: dict[str, Any]
    recipe_overrides: dict[str, Any]
    output_requirements: tuple[str, ...]
    engine_version: str
    is_executable: bool
    source_row_id: str
    raw_values: dict[str, Any] = field(default_factory=dict)
