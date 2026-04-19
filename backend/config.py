"""
backend/config.py — Centralized configuration for Farmer's Chat v2.
"""
import os
from dotenv import load_dotenv

# Load .env from project root (one level up from backend/)
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
DATA_GOV_API_KEY: str = os.getenv("DATA_GOV_API_KEY", "")
WEATHER_API_KEY: str = os.getenv("WEATHER_API_KEY", "")  # OpenWeatherMap (optional)

# Path to the CSV file one level up
CSV_PATH: str = os.path.join(os.path.dirname(__file__), "..", "Fert&Pest.csv")

DATABASE_URL: str = os.path.join(os.path.dirname(__file__), "chat_history.db")

if not GROQ_API_KEY:
    raise EnvironmentError("GROQ_API_KEY not set. Check your .env file.")
