"""
backend/services/agri_data.py — CSV-based fertilizer and pesticide lookups.
CSV loaded once at import time for performance.
"""
import pandas as pd
from config import CSV_PATH

try:
    _df = pd.read_csv(CSV_PATH)
    _df.columns = _df.columns.str.strip()
    _df["Commodity"] = _df["Commodity"].str.lower().str.strip()
except FileNotFoundError:
    raise FileNotFoundError(f"Agri data CSV not found at: {CSV_PATH}")


def _lookup(crop: str, column: str) -> str | None:
    """Smart lookup with plural stripping and partial match fallback."""
    normalized = crop.lower().strip()
    candidates = [normalized, normalized.rstrip("s")]
    if normalized.endswith("es"):
        candidates.append(normalized[:-2])

    for candidate in candidates:
        result = _df[_df["Commodity"] == candidate]
        if not result.empty:
            return result[column].values[0]

    # Partial match
    result = _df[_df["Commodity"].str.contains(normalized, na=False)]
    if not result.empty:
        return result[column].values[0]

    return None


def fetch_pesticide_recommendations(crop: str) -> str | None:
    return _lookup(crop, "Pesticides")


def fetch_fertilizer_recommendations(crop: str) -> str | None:
    return _lookup(crop, "Fertilizers")
