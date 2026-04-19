"""
backend/services/weather.py — OpenWeatherMap integration.
Gracefully returns None if no API key is configured.
"""
import requests
from config import WEATHER_API_KEY

_BASE_URL = "https://api.openweathermap.org/data/2.5/weather"


def get_weather(city: str) -> dict | None:
    """
    Fetch current weather for a city.
    Returns a dict with relevant fields, or None if unavailable.
    """
    if not WEATHER_API_KEY:
        return None

    try:
        response = requests.get(
            _BASE_URL,
            params={
                "q": city,
                "appid": WEATHER_API_KEY,
                "units": "metric",
            },
            timeout=8,
        )
        response.raise_for_status()
        data = response.json()

        weather = data["weather"][0]
        main = data["main"]
        wind = data.get("wind", {})
        rain = data.get("rain", {})

        return {
            "city": data["name"],
            "country": data["sys"]["country"],
            "condition": weather["main"],
            "description": weather["description"].capitalize(),
            "temp_c": round(main["temp"]),
            "feels_like_c": round(main["feels_like"]),
            "humidity_pct": main["humidity"],
            "wind_kmh": round(wind.get("speed", 0) * 3.6),
            "rain_1h_mm": rain.get("1h", 0),
            "icon": weather["icon"],
        }
    except Exception:
        return None


def build_weather_farming_tip(weather: dict) -> str:
    """Generate quick farming advice based on weather conditions."""
    tips = []

    if weather["rain_1h_mm"] > 5:
        tips.append("Heavy rain expected — avoid spraying pesticides or fertilizers today.")
    elif weather["rain_1h_mm"] > 0:
        tips.append("Light rain — hold off on irrigation, natural watering is sufficient.")
    else:
        tips.append("No rain — consider irrigation if soil moisture is low.")

    if weather["temp_c"] > 38:
        tips.append("Extreme heat — water crops early morning or evening to reduce evaporation.")
    elif weather["temp_c"] < 10:
        tips.append("Cold weather — protect frost-sensitive crops with covers overnight.")

    if weather["humidity_pct"] > 80:
        tips.append("High humidity — watch for fungal diseases. Ensure good crop airflow.")
    elif weather["humidity_pct"] < 30:
        tips.append("Low humidity — increase irrigation frequency.")

    if weather["wind_kmh"] > 40:
        tips.append("Strong winds — avoid spraying chemicals (drift risk).")

    return " ".join(tips) if tips else "Weather looks fine for farming activities today."
