"""Deterministic engineering calculations for the Porous Lane prototype."""

from __future__ import annotations


def porosity_from_void_ratio(void_ratio: float) -> float:
    """Convert void ratio e to porosity n."""
    if void_ratio < 0:
        raise ValueError("Void ratio cannot be negative.")
    return void_ratio / (1.0 + void_ratio)


def layer_storage_m3(
    area_m2: float,
    thickness_mm: float,
    porosity: float,
) -> float:
    """Return void storage capacity for a layer in cubic metres."""
    if area_m2 < 0 or thickness_mm < 0:
        raise ValueError("Area and thickness cannot be negative.")
    if not 0 <= porosity < 1:
        raise ValueError("Porosity must be between 0 and 1.")
    return area_m2 * (thickness_mm / 1000.0) * porosity


def rainfall_depth_mm(
    intensity_mm_h: float,
    duration_min: float,
) -> float:
    """Convert average rainfall intensity to event rainfall depth."""
    if intensity_mm_h < 0 or duration_min < 0:
        raise ValueError("Rainfall intensity and duration cannot be negative.")
    return intensity_mm_h * (duration_min / 60.0)


def rainfall_volume_m3(
    catchment_area_m2: float,
    rainfall_depth_mm_value: float,
) -> float:
    """Return event rainfall volume over the contributing catchment."""
    if catchment_area_m2 < 0 or rainfall_depth_mm_value < 0:
        raise ValueError("Catchment area and rainfall depth cannot be negative.")
    return catchment_area_m2 * rainfall_depth_mm_value / 1000.0


def retained_volume_m3(
    rainfall_volume: float,
    storage_capacity: float,
) -> float:
    return min(max(rainfall_volume, 0.0), max(storage_capacity, 0.0))


def overflow_volume_m3(
    rainfall_volume: float,
    storage_capacity: float,
) -> float:
    return max(0.0, rainfall_volume - storage_capacity)


def volume_reduction_fraction(
    storage_capacity: float,
    rainfall_volume: float,
) -> float:
    """Return theoretical event runoff-volume reduction, capped at 100%."""
    if rainfall_volume <= 0:
        return 0.0
    return min(1.0, max(storage_capacity, 0.0) / rainfall_volume)


def capacity_status(
    rainfall_volume: float,
    storage_capacity: float,
) -> str:
    return (
        "Overflow"
        if rainfall_volume > storage_capacity
        else "Within capacity"
    )
