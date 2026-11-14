"""Fuel station data access.

The assessment CSV ships without coordinates. A one-time offline step
(scripts/geocode_stations.py) geocodes every station (US Census batch
geocoder, city/state centroid fallback) and commits the results to
data/fuel_stations_geocoded.csv. At runtime we just load that file into
memory once - ~6.7k rows, so this is cheap and per-request work stays at zero.
"""
import csv
import logging
from dataclasses import dataclass

from django.conf import settings

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Station:
    opis_id: str
    name: str
    address: str
    city: str
    state: str
    price: float  # retail price per gallon
    lat: float
    lon: float
    geocode_quality: str  # "address" | "city_centroid"


_cache: list[Station] | None = None


def load_stations() -> list[Station]:
    """Load and memoize the full station list (skips ungeocoded rows)."""
    global _cache
    if _cache is not None:
        return _cache

    stations: list[Station] = []
    skipped = 0
    with open(settings.FUEL_DATA_FILE, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if not row["lat"] or not row["lon"]:
                skipped += 1
                continue
            stations.append(
                Station(
                    opis_id=row["opis_id"],
                    name=row["name"],
                    address=row["address"],
                    city=row["city"],
                    state=row["state"],
                    price=float(row["retail_price"]),
                    lat=float(row["lat"]),
                    lon=float(row["lon"]),
                    geocode_quality=row["geocode_quality"],
                )
            )
    if skipped:
        logger.warning("Skipped %d stations without coordinates", skipped)
    _cache = stations
    return stations


def reset_cache() -> None:
    """Test hook."""
    global _cache
    _cache = None
