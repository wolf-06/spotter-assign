"""Start/finish geocoding via Nominatim (free, no key).

Results are cached aggressively - repeated demo requests make zero calls.
Nominatim's usage policy asks for a real User-Agent and <=1 req/s, which
caching gives us for free in practice.
"""
import requests
from django.conf import settings
from django.core.cache import cache


class GeocodeError(Exception):
    pass


def geocode_place(query: str) -> dict:
    """Resolve a US place string to {'lat', 'lon', 'display_name'}.

    Raises GeocodeError when the place cannot be resolved or is not in the US.
    """
    key = "geocode:" + " ".join(query.lower().split())
    hit = cache.get(key)
    if hit:
        return hit

    try:
        resp = requests.get(
            f"{settings.NOMINATIM_BASE_URL}/search",
            params={
                "q": query,
                "format": "json",
                "addressdetails": 1,
                "limit": 1,
                "countrycodes": "us",
            },
            headers={"User-Agent": "spotter-fuel-route-api (coding assessment)"},
            timeout=10,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        raise GeocodeError(f"geocoding service unavailable: {exc}") from exc

    results = resp.json()
    if not results:
        raise GeocodeError(f"could not resolve location: {query!r}")

    r = results[0]
    if r.get("address", {}).get("country_code") != "us":
        raise GeocodeError(f"location is not within the USA: {query!r}")

    out = {
        "lat": float(r["lat"]),
        "lon": float(r["lon"]),
        "display_name": r["display_name"],
    }
    cache.set(key, out, settings.GEOCODE_CACHE_SECONDS)
    return out
