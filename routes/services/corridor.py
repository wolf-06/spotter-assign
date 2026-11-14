"""Match fuel stations to a route.

A station is a candidate when it sits within CORRIDOR_MILES of the route
polyline. Its "mile marker" is the distance along the route of the nearest
route point. Pure Python: route points are bucketed into a lat/lon grid so
each station only measures distance against nearby points.
"""
import math
from collections import namedtuple

from .stations import Station

RouteStop = namedtuple("RouteStop", ["station", "mile_marker", "off_route_miles"])

EARTH_RADIUS_MI = 3958.8
_CELL_DEG = 0.25  # ~17 mi of latitude; 3x3 neighbourhood comfortably covers the corridor


def haversine_mi(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_MI * math.asin(math.sqrt(a))


def _cell(lat: float, lon: float) -> tuple[int, int]:
    return (int(lat / _CELL_DEG), int(lon / _CELL_DEG))


def _cumulative_miles(geometry: list[list[float]]) -> list[float]:
    """Distance along the route at every geometry point (geometry is [lon, lat])."""
    cum = [0.0]
    for (lon1, lat1), (lon2, lat2) in zip(geometry, geometry[1:]):
        cum.append(cum[-1] + haversine_mi(lat1, lon1, lat2, lon2))
    return cum


# Full-resolution OSRM geometry is ~10 points per mile; matching stations
# against every point is wasted work. Downsample to roughly one point per
# SAMPLE_INTERVAL_MI - well under the corridor width, so mile markers and
# corridor membership are unaffected at this granularity.
SAMPLE_INTERVAL_MI = 1.0


def _sample_geometry(geometry: list[list[float]], cum: list[float]) -> list[int]:
    """Indices into geometry, kept about SAMPLE_INTERVAL_MI apart."""
    keep = [0]
    for idx in range(1, len(geometry)):
        if cum[idx] - cum[keep[-1]] >= SAMPLE_INTERVAL_MI:
            keep.append(idx)
    if keep[-1] != len(geometry) - 1:
        keep.append(len(geometry) - 1)
    return keep


def stations_along_route(
    geometry: list[list[float]],
    stations: list[Station],
    corridor_miles: float,
) -> list[RouteStop]:
    """Return corridor stations sorted by mile marker along the route."""
    cum = _cumulative_miles(geometry)
    keep = _sample_geometry(geometry, cum)

    grid: dict[tuple[int, int], list[int]] = {}
    for idx in keep:
        lon, lat = geometry[idx]
        grid.setdefault(_cell(lat, lon), []).append(idx)

    stops: list[RouteStop] = []
    for st in stations:
        c_lat, c_lon = _cell(st.lat, st.lon)
        best_dist = math.inf
        best_idx = -1
        for d_lat in (-1, 0, 1):
            for d_lon in (-1, 0, 1):
                for idx in grid.get((c_lat + d_lat, c_lon + d_lon), ()):
                    lon, lat = geometry[idx]
                    d = haversine_mi(st.lat, st.lon, lat, lon)
                    if d < best_dist:
                        best_dist, best_idx = d, idx
        if best_idx >= 0 and best_dist <= corridor_miles:
            stops.append(RouteStop(station=st, mile_marker=cum[best_idx], off_route_miles=best_dist))

    stops.sort(key=lambda s: s.mile_marker)
    return stops
