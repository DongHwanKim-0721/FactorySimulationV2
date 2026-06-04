from __future__ import annotations

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class WeeklyProductionResult:
    is_available: bool
    weekly_expected_tons: float
    output_quantity_ea: float
    weekly_expected_output_ea: float
    elapsed_minutes: float
    available_minutes: float
    realized_throughput_ea_per_min: float
    message: str = ""


def calculate_weekly_expected_production(
    *,
    output_quantity_ea: float,
    elapsed_minutes: float,
    unit_weight_kg_per_ea: float,
    operating_days: float,
    daily_hours: float,
    operating_rate_percent: float,
) -> WeeklyProductionResult:
    """Convert realized simulation output into expected weekly tons."""
    _validate_inputs(
        output_quantity_ea=output_quantity_ea,
        elapsed_minutes=elapsed_minutes,
        unit_weight_kg_per_ea=unit_weight_kg_per_ea,
        operating_days=operating_days,
        daily_hours=daily_hours,
        operating_rate_percent=operating_rate_percent,
    )

    realized_throughput_ea_per_min = (
        output_quantity_ea / elapsed_minutes if elapsed_minutes > 0 else 0.0
    )
    available_minutes = (
        operating_days * daily_hours * 60 * operating_rate_percent / 100
    )
    if elapsed_minutes > 0:
        weekly_expected_output_ea = min(
            output_quantity_ea,
            realized_throughput_ea_per_min * available_minutes,
        )
    else:
        weekly_expected_output_ea = output_quantity_ea
    weekly_expected_tons = weekly_expected_output_ea * unit_weight_kg_per_ea / 1000

    return WeeklyProductionResult(
        is_available=True,
        weekly_expected_tons=weekly_expected_tons,
        output_quantity_ea=output_quantity_ea,
        weekly_expected_output_ea=weekly_expected_output_ea,
        elapsed_minutes=elapsed_minutes,
        available_minutes=available_minutes,
        realized_throughput_ea_per_min=realized_throughput_ea_per_min,
    )


def _validate_inputs(
    *,
    output_quantity_ea: float,
    elapsed_minutes: float,
    unit_weight_kg_per_ea: float,
    operating_days: float,
    daily_hours: float,
    operating_rate_percent: float,
) -> None:
    if not isfinite(output_quantity_ea) or output_quantity_ea < 0:
        raise ValueError("output_quantity_ea must be 0 or greater.")
    if not isfinite(elapsed_minutes) or elapsed_minutes < 0:
        raise ValueError("elapsed_minutes must be 0 or greater.")
    if not isfinite(unit_weight_kg_per_ea) or unit_weight_kg_per_ea <= 0:
        raise ValueError("unit_weight_kg_per_ea must be greater than 0.")
    if not isfinite(operating_days) or operating_days < 0 or operating_days > 7:
        raise ValueError("operating_days must be between 0 and 7.")
    if not isfinite(daily_hours) or daily_hours < 0 or daily_hours > 24:
        raise ValueError("daily_hours must be between 0 and 24.")
    if (
        not isfinite(operating_rate_percent)
        or operating_rate_percent < 0
        or operating_rate_percent > 100
    ):
        raise ValueError("operating_rate_percent must be between 0 and 100.")
