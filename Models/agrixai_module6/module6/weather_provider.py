"""
weather_provider.py
===================
Pluggable weather interface.

Module 6 must reason about temperature/humidity to break ties (e.g. Yellow vs.
Brown Rust). We define an abstract `WeatherProvider` so the user can later
plug in OpenWeatherMap, Tomorrow.io, or local sensors without touching the
rule engine.

Two implementations ship in this module:
  - MockWeatherProvider:   returns a fixed reading (configurable). Useful for
                           unit tests and Colab demos.
  - DictWeatherProvider:   wraps a plain dict you pass at controller call time.
                           Intended for the case where your front-end already
                           queried the weather and just hands the values to us.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class WeatherReading:
    """Standardised weather snapshot used by the rule engine.

    All fields are Optional because real-world providers may not expose
    every sensor. Rules must handle missing data gracefully (treat as
    'unknown' rather than 'zero').
    """

    temperature_c: Optional[float] = None      # Celsius
    humidity_pct: Optional[float] = None       # 0-100
    rainfall_mm_24h: Optional[float] = None    # mm of rain in last 24h
    wind_kmh: Optional[float] = None
    season: Optional[str] = None               # 'spring' | 'summer' | 'autumn' | 'winter'
    growth_stage: Optional[str] = None         # 'flowering' | 'maturation' | 'vegetative' | ...
    location_name: Optional[str] = None        # for reports

    def is_high_humidity(self, threshold: float = 80.0) -> bool:
        return self.humidity_pct is not None and self.humidity_pct >= threshold

    def temp_in_range(self, lo: float, hi: float) -> bool:
        return self.temperature_c is not None and lo <= self.temperature_c <= hi

    def to_dict(self) -> dict:
        return {
            "temperature_c": self.temperature_c,
            "humidity_pct": self.humidity_pct,
            "rainfall_mm_24h": self.rainfall_mm_24h,
            "wind_kmh": self.wind_kmh,
            "season": self.season,
            "growth_stage": self.growth_stage,
            "location_name": self.location_name,
        }


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

class WeatherProvider(ABC):
    """Abstract base. Implementations must return a WeatherReading."""

    @abstractmethod
    def get(self, lat: Optional[float] = None, lon: Optional[float] = None) -> WeatherReading:
        ...


# ---------------------------------------------------------------------------
# Built-in implementations
# ---------------------------------------------------------------------------

class MockWeatherProvider(WeatherProvider):
    """Returns a fixed WeatherReading. Configurable in __init__."""

    def __init__(self, reading: Optional[WeatherReading] = None) -> None:
        # Defaults reflect a fairly typical late-spring Egyptian Delta morning,
        # which happens to be a Yellow Rust risk window — useful for demos.
        self._reading = reading or WeatherReading(
            temperature_c=14.0,
            humidity_pct=92.0,
            rainfall_mm_24h=2.0,
            wind_kmh=8.0,
            season="spring",
            growth_stage="flowering",
            location_name="Tanta, Gharbia, EG (mock)",
        )

    def get(self, lat: Optional[float] = None, lon: Optional[float] = None) -> WeatherReading:
        return self._reading

    def set_reading(self, reading: WeatherReading) -> None:
        """Allows tests / demos to mutate the mock at runtime."""
        self._reading = reading


class DictWeatherProvider(WeatherProvider):
    """Wraps a plain dict. Useful when the caller already has weather data."""

    def __init__(self, data: dict) -> None:
        self._data = data

    def get(self, lat: Optional[float] = None, lon: Optional[float] = None) -> WeatherReading:
        d = self._data
        return WeatherReading(
            temperature_c=d.get("temperature_c") or d.get("temp"),
            humidity_pct=d.get("humidity_pct") or d.get("humidity"),
            rainfall_mm_24h=d.get("rainfall_mm_24h") or d.get("rain"),
            wind_kmh=d.get("wind_kmh") or d.get("wind"),
            season=d.get("season"),
            growth_stage=d.get("growth_stage"),
            location_name=d.get("location_name") or d.get("location"),
        )


# ---------------------------------------------------------------------------
# Adapter contract for real providers (OpenWeatherMap, Tomorrow.io, ...)
# ---------------------------------------------------------------------------

# To plug in a real provider later, subclass WeatherProvider and implement
# .get(). Example skeleton:
#
#     class OpenWeatherMapProvider(WeatherProvider):
#         def __init__(self, api_key: str): self.api_key = api_key
#         def get(self, lat, lon):
#             import requests
#             r = requests.get("https://api.openweathermap.org/data/2.5/weather",
#                              params={"lat": lat, "lon": lon, "appid": self.api_key,
#                                      "units": "metric"}).json()
#             return WeatherReading(
#                 temperature_c=r["main"]["temp"],
#                 humidity_pct=r["main"]["humidity"],
#                 wind_kmh=r["wind"]["speed"] * 3.6,
#                 location_name=r.get("name"),
#             )
