"""State-level benchmark tables and default operating assumptions.

These are rough state averages carried over from the prototype. They have NOT been
independently re-sourced, are not property-specific, and must always be presented as
low-confidence estimates (spec §5.2).
"""

from typing import Optional, Tuple

SOURCE = "Prototype state-average constants (not independently verified)"
AS_OF = "carried over from the initial prototype; undated"

TAX_RATES = {
    "AL": 0.39,
    "AK": 1.17,
    "AZ": 0.62,
    "AR": 0.63,
    "CA": 0.74,
    "CO": 0.48,
    "CT": 2.14,
    "DE": 0.56,
    "FL": 0.89,
    "GA": 0.83,
    "HI": 0.28,
    "ID": 0.63,
    "IL": 2.07,
    "IN": 0.84,
    "IA": 1.52,
    "KS": 1.33,
    "KY": 0.86,
    "LA": 0.55,
    "ME": 1.09,
    "MD": 1.08,
    "MA": 1.14,
    "MI": 1.32,
    "MN": 1.11,
    "MS": 0.64,
    "MO": 0.96,
    "MT": 0.74,
    "NE": 1.54,
    "NV": 0.55,
    "NH": 2.09,
    "NJ": 2.23,
    "NM": 0.67,
    "NY": 1.40,
    "NC": 0.78,
    "ND": 0.98,
    "OH": 1.59,
    "OK": 0.89,
    "OR": 0.91,
    "PA": 1.49,
    "RI": 1.53,
    "SC": 0.57,
    "SD": 1.17,
    "TN": 0.66,
    "TX": 1.63,
    "UT": 0.52,
    "VT": 1.78,
    "VA": 0.75,
    "WA": 0.92,
    "WV": 0.59,
    "WI": 1.73,
    "WY": 0.57,
}
INS_RATES = {
    "AL": 0.55,
    "AK": 0.38,
    "AZ": 0.45,
    "AR": 0.70,
    "CA": 0.42,
    "CO": 0.58,
    "CT": 0.60,
    "DE": 0.43,
    "FL": 1.30,
    "GA": 0.65,
    "HI": 0.30,
    "ID": 0.45,
    "IL": 0.62,
    "IN": 0.72,
    "IA": 0.78,
    "KS": 1.25,
    "KY": 0.75,
    "LA": 1.10,
    "ME": 0.70,
    "MD": 0.55,
    "MA": 0.68,
    "MI": 0.82,
    "MN": 0.88,
    "MS": 0.90,
    "MO": 0.95,
    "MT": 0.50,
    "NE": 1.00,
    "NV": 0.38,
    "NH": 0.60,
    "NJ": 0.68,
    "NM": 0.48,
    "NY": 0.58,
    "NC": 0.72,
    "ND": 0.80,
    "OH": 0.70,
    "OK": 1.30,
    "OR": 0.40,
    "PA": 0.55,
    "RI": 0.75,
    "SC": 0.75,
    "SD": 0.78,
    "TN": 0.72,
    "TX": 1.55,
    "UT": 0.40,
    "VT": 0.55,
    "VA": 0.52,
    "WA": 0.44,
    "WV": 0.65,
    "WI": 0.56,
    "WY": 0.50,
}
RENT_PRICE_RATIO = {
    "TX": 0.0070,
    "FL": 0.0082,
    "AZ": 0.0075,
    "GA": 0.0078,
    "NC": 0.0074,
    "OH": 0.0098,
    "MI": 0.0095,
    "PA": 0.0082,
    "IL": 0.0079,
    "CO": 0.0062,
    "WA": 0.0060,
    "CA": 0.0052,
    "NY": 0.0058,
    "NV": 0.0070,
    "TN": 0.0078,
    "VA": 0.0065,
    "SC": 0.0076,
    "MO": 0.0085,
    "IN": 0.0090,
    "KY": 0.0088,
    "AL": 0.0085,
    "MS": 0.0090,
    "AR": 0.0088,
    "LA": 0.0080,
}
STATE_COST = {
    "TX": 1.05,
    "FL": 1.18,
    "CA": 1.95,
    "NY": 1.80,
    "CO": 1.40,
    "WA": 1.50,
    "AZ": 1.10,
    "GA": 1.02,
    "NC": 0.95,
    "OH": 0.88,
    "MI": 0.85,
    "IL": 1.08,
    "PA": 0.97,
    "NV": 1.12,
    "TN": 0.90,
    "VA": 1.15,
    "SC": 0.93,
    "NJ": 1.55,
    "MA": 1.65,
    "MD": 1.25,
    "OR": 1.28,
}
BASE_RENTS = {1: 1100, 2: 1420, 3: 1850, 4: 2300, 5: 2900}

STATES = frozenset(TAX_RATES)

# Fallbacks when a state is missing from the rent tables only. Always disclosed in the basis text.
DEFAULT_RENT_PRICE_RATIO = 0.007
DEFAULT_STATE_COST = 1.0

# Default operating assumptions (spec §5.2).
VACANCY_PCT = 5.0
MANAGEMENT_PCT = 8.0
CAPEX_PCT_OF_PRICE_PER_YEAR = 1.0


def estimate_rent(price: float, beds: int, state: str) -> Optional[Tuple[int, str]]:
    """Blend of rent-to-price and bedroom benchmarks, rounded to $25, or None if unsupported."""
    base = BASE_RENTS.get(beds)
    if base is None:
        return None
    ratio = RENT_PRICE_RATIO.get(state)
    cost = STATE_COST.get(state)
    note = ""
    if ratio is None or cost is None:
        note = f" No {state} benchmark in our tables, so national fallback values were used."
        ratio = DEFAULT_RENT_PRICE_RATIO if ratio is None else ratio
        cost = DEFAULT_STATE_COST if cost is None else cost
    rent = round((price * ratio * 0.5 + base * cost * 0.5) / 25) * 25
    basis = (
        f"50% price × {ratio:.4f} rent-to-price ratio + 50% {beds}-bedroom benchmark "
        f"${base:,} × {cost:.2f} cost index, rounded to $25. A state-level benchmark, "
        f"not a market quote.{note}"
    )
    return int(rent), basis
