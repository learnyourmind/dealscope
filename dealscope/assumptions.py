"""State-level insurance/tax benchmark tables and default assumptions.

These are rough state averages carried over from the prototype. They have NOT been
independently re-sourced, are not property-specific, and must always be presented as
low-confidence estimates (spec §5.2).
"""

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

STATES = frozenset(TAX_RATES)

# Bedroom scaling of the ZIP's typical rent. Prototype benchmark rents by bedroom count
# (1BR $1,100 ... 4BR $2,300) divided by their 2BR/3BR midpoint ($1,635), which stands in for
# "typical". A rough, unverified heuristic: always shown as a low-confidence estimate.
BEDROOM_RENT_FACTORS = {1: 0.67, 2: 0.87, 3: 1.13, 4: 1.41}
BEDROOM_FACTOR_BASIS = (
    "Typical ZIP rent scaled by a rough bedroom factor "
    "(1BR 0.67, 2BR 0.87, 3BR 1.13, 4BR 1.41) from prototype benchmarks; not market data."
)

# Default operating assumptions (spec §5.2).
VACANCY_PCT = 5.0
MANAGEMENT_PCT = 8.0
CAPEX_PCT_OF_PRICE_PER_YEAR = 1.0
