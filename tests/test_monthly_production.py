import pytest

from engine.weekly_production import calculate_weekly_expected_production


def test_weekly_expected_production_converts_final_output_to_tons_when_time_is_enough():
    result = calculate_weekly_expected_production(
        output_quantity_ea=10,
        elapsed_minutes=20,
        unit_weight_kg_per_ea=2,
        operating_days=1,
        daily_hours=1,
        operating_rate_percent=100,
    )

    assert result.is_available is True
    assert result.realized_throughput_ea_per_min == pytest.approx(0.5)
    assert result.weekly_expected_output_ea == pytest.approx(10)
    assert result.weekly_expected_tons == pytest.approx(0.02)


def test_weekly_expected_production_is_capped_by_final_output_quantity():
    result = calculate_weekly_expected_production(
        output_quantity_ea=10,
        elapsed_minutes=20,
        unit_weight_kg_per_ea=100,
        operating_days=5,
        daily_hours=24,
        operating_rate_percent=100,
    )

    assert result.weekly_expected_output_ea == pytest.approx(10)
    assert result.weekly_expected_tons == pytest.approx(1)


def test_weekly_expected_production_can_decrease_when_available_time_is_short():
    result = calculate_weekly_expected_production(
        output_quantity_ea=10,
        elapsed_minutes=20,
        unit_weight_kg_per_ea=100,
        operating_days=1,
        daily_hours=10 / 60,
        operating_rate_percent=100,
    )

    assert result.weekly_expected_output_ea == pytest.approx(5)
    assert result.weekly_expected_tons == pytest.approx(0.5)


def test_weekly_expected_production_uses_operating_rate_inside_the_output_cap():
    result = calculate_weekly_expected_production(
        output_quantity_ea=10,
        elapsed_minutes=20,
        unit_weight_kg_per_ea=100,
        operating_days=1,
        daily_hours=20 / 60,
        operating_rate_percent=50,
    )

    assert result.available_minutes == pytest.approx(10)
    assert result.weekly_expected_output_ea == pytest.approx(5)
    assert result.weekly_expected_tons == pytest.approx(0.5)


def test_weekly_expected_production_uses_unit_weight():
    result = calculate_weekly_expected_production(
        output_quantity_ea=20,
        elapsed_minutes=10,
        unit_weight_kg_per_ea=3,
        operating_days=1,
        daily_hours=1,
        operating_rate_percent=100,
    )

    assert result.weekly_expected_tons == pytest.approx(0.06)


def test_weekly_expected_production_allows_zero_output():
    result = calculate_weekly_expected_production(
        output_quantity_ea=0,
        elapsed_minutes=20,
        unit_weight_kg_per_ea=1,
        operating_days=5,
        daily_hours=24,
        operating_rate_percent=100,
    )

    assert result.is_available is True
    assert result.realized_throughput_ea_per_min == 0
    assert result.weekly_expected_tons == 0


@pytest.mark.parametrize(
    "kwargs, error",
    [
        ({"output_quantity_ea": -1}, "output_quantity"),
        ({"elapsed_minutes": -1}, "elapsed_minutes"),
        ({"unit_weight_kg_per_ea": 0}, "unit_weight"),
        ({"operating_days": -1}, "operating_days"),
        ({"operating_days": 8}, "operating_days"),
        ({"daily_hours": -1}, "daily_hours"),
        ({"daily_hours": 25}, "daily_hours"),
        ({"operating_rate_percent": -1}, "operating_rate"),
        ({"operating_rate_percent": 101}, "operating_rate"),
    ],
)
def test_weekly_expected_production_rejects_invalid_inputs(kwargs, error):
    params = {
        "output_quantity_ea": 10,
        "elapsed_minutes": 20,
        "unit_weight_kg_per_ea": 1,
        "operating_days": 5,
        "daily_hours": 24,
        "operating_rate_percent": 100,
    }
    params.update(kwargs)

    with pytest.raises(ValueError, match=error):
        calculate_weekly_expected_production(**params)


def test_weekly_expected_production_allows_zero_elapsed_time():
    result = calculate_weekly_expected_production(
        output_quantity_ea=10,
        elapsed_minutes=0,
        unit_weight_kg_per_ea=100,
        operating_days=5,
        daily_hours=24,
        operating_rate_percent=100,
    )

    assert result.is_available is True
    assert result.weekly_expected_output_ea == pytest.approx(10)
    assert result.weekly_expected_tons == pytest.approx(1)
    assert result.realized_throughput_ea_per_min == 0
