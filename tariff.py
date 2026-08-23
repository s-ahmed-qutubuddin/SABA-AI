"""Configurable Telangana household electricity estimate for Saba.

This module intentionally uses the user's supplied Saidabad/Hyderabad
schedule. It is an ESTIMATE: an actual utility bill can contain other
charges/adjustments and tariffs can change.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class Slab:
    start: float
    end: Optional[float]
    rate: float
    consumer_charge: float


# User-supplied schedule.
SLABS = (
    Slab(0, 50, 1.45, 40.0),
    Slab(50, 100, 2.60, 70.0),
    Slab(100, 200, 3.75, 90.0),
    Slab(200, 300, 5.25, 100.0),
    Slab(300, 400, 6.60, 120.0),
    Slab(400, 800, 7.65, 140.0),
    Slab(800, None, 9.50, 160.0),
)


def estimate_household_bill(units: float) -> dict:
    """Progressive/telescopic estimate for monthly household units."""
    if units < 0:
        raise ValueError("Units must be non-negative")

    remaining = float(units)
    energy_charge = 0.0
    breakdown = []

    for slab in SLABS:
        if remaining <= 0:
            break

        width = None if slab.end is None else slab.end - slab.start
        used = remaining if width is None else min(remaining, width)

        charge = used * slab.rate
        energy_charge += charge
        breakdown.append(
            {
                "from_unit": slab.start,
                "to_unit": slab.end,
                "units": round(used, 6),
                "rate_per_unit": slab.rate,
                "charge": round(charge, 2),
            }
        )
        remaining -= used

    consumer_charge = _consumer_charge_for_total(units)
    total = energy_charge + consumer_charge

    return {
        "ok": True,
        "schedule": "user_supplied_telangana_household",
        "units": round(units, 3),
        "energy_charge": round(energy_charge, 2),
        "consumer_charge": round(consumer_charge, 2),
        "estimated_bill": round(total, 2),
        "breakdown": breakdown,
        "note": "Estimate based on the user-supplied slab schedule; actual utility bills may include additional charges/adjustments.",
    }


def _consumer_charge_for_total(units: float) -> float:
    for slab in SLABS:
        if slab.end is None or units <= slab.end:
            return slab.consumer_charge
    return SLABS[-1].consumer_charge


def estimate_ac_share(
    ac_units: float,
    household_units: float,
) -> dict:
    """Estimate incremental household bill attributable to an AC.

    This avoids pretending an AC has its own tariff slab. The AC's
    incremental cost is bill(total household usage) - bill(without AC).
    """
    if ac_units < 0 or household_units < 0:
        raise ValueError("Units must be non-negative")
    if ac_units > household_units:
        raise ValueError("AC units cannot exceed household units")

    whole = estimate_household_bill(household_units)
    without_ac = estimate_household_bill(household_units - ac_units)
    incremental = whole["estimated_bill"] - without_ac["estimated_bill"]

    return {
        "ok": True,
        "ac_units": round(ac_units, 3),
        "household_units": round(household_units, 3),
        "estimated_ac_increment": round(incremental, 2),
        "household_bill_with_ac": whole["estimated_bill"],
        "household_bill_without_ac": without_ac["estimated_bill"],
    }
