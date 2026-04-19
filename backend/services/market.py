"""
backend/services/market.py — Government market price data fetcher.
"""
import requests
from config import DATA_GOV_API_KEY

_API_URL = "https://api.data.gov.in/resource/9ef84268-d588-465a-a308-a864a43d0070"


def get_market_price(commodity: str, state: str) -> dict:
    """
    Fetch current market prices for a commodity in a given state.
    Returns a dict with 'records' list and 'text' summary.
    """
    params = {
        "api-key": DATA_GOV_API_KEY,
        "format": "json",
        "filters[commodity]": commodity,
        "filters[state]": state,
        "limit": 100,
    }
    try:
        response = requests.get(_API_URL, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()

        if "records" in data and data["records"]:
            records = [
                {
                    "market": r["market"],
                    "price": int(r["modal_price"]),
                    "min_price": int(r.get("min_price", r["modal_price"])),
                    "max_price": int(r.get("max_price", r["modal_price"])),
                    "date": r["arrival_date"],
                }
                for r in data["records"]
            ]
            summary = "\n".join(
                f"• {r['market']}: ₹{r['price']}/quintal ({r['date']})"
                for r in records[:10]
            )
            return {"records": records, "text": summary, "found": True}
        return {
            "records": [],
            "text": f"No market data found for **{commodity}** in **{state}**.",
            "found": False,
        }
    except requests.exceptions.RequestException as e:
        return {"records": [], "text": f"Error fetching market data: {e}", "found": False}
