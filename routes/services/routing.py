"""Routing via the public OSRM demo server (free, no key).

Exactly one routing API call per route computation: a single
/route/v1/driving request with full GeoJSON geometry.
"""
import requests
from django.conf import settings


class RoutingError(Exception):
    pass


def get_route(start: dict, finish: dict) -> dict:
    """Return {'distance_miles', 'duration_hours', 'geometry': [[lon, lat], ...]}."""
    coords = f"{start['lon']},{start['lat']};{finish['lon']},{finish['lat']}"
    try:
        resp = requests.get(
            f"{settings.OSRM_BASE_URL}/route/v1/driving/{coords}",
            params={
                "overview": "full",
                "geometries": "geojson",
                "steps": "false",
            },
            timeout=30,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise RoutingError(f"routing service unavailable: {exc}") from exc

    payload = resp.json()
    if payload.get("code") != "Ok" or not payload.get("routes"):
        raise RoutingError(f"no route found between the two locations ({payload.get('code')})")

    route = payload["routes"][0]
    return {
        "distance_miles": route["distance"] / 1609.344,
        "duration_hours": route["duration"] / 3600.0,
        "geometry": route["geometry"]["coordinates"],  # [[lon, lat], ...]
    }
