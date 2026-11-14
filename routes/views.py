import hashlib
import logging
import time
from concurrent.futures import ThreadPoolExecutor

from django.conf import settings
from django.core.cache import cache
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from .services import corridor, geocoding, optimizer, routing, stations

logger = logging.getLogger(__name__)


def _norm_place(value: str) -> str:
    return " ".join(value.lower().split())


class RouteView(APIView):
    """Plan the cheapest fuel stops between two US locations.

    POST {"start": "New York, NY", "finish": "Los Angeles, CA"}
    GET  /api/route/?start=...&finish=...
    """

    def get(self, request):
        return self._handle(request.query_params)

    def post(self, request):
        return self._handle(request.data)

    def _handle(self, params):
        started = time.perf_counter()
        start = (params.get("start") or "").strip()
        finish = (params.get("finish") or "").strip()
        if not start or not finish:
            return Response(
                {"detail": "Both 'start' and 'finish' are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        cache_key = "route:" + hashlib.sha256(
            f"{_norm_place(start)}|{_norm_place(finish)}".encode()
        ).hexdigest()
        cached = cache.get(cache_key)
        if cached:
            cached["meta"]["cache_hit"] = True
            cached["meta"]["elapsed_ms"] = round((time.perf_counter() - started) * 1000, 1)
            return Response(cached)

        # Geocode both endpoints in parallel (cached; Nominatim, US only).
        try:
            with ThreadPoolExecutor(max_workers=2) as pool:
                start_fut = pool.submit(geocoding.geocode_place, start)
                finish_fut = pool.submit(geocoding.geocode_place, finish)
                start_geo = start_fut.result()
                finish_geo = finish_fut.result()
        except geocoding.GeocodeError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        # One routing call (OSRM) with full route geometry.
        try:
            route = routing.get_route(start_geo, finish_geo)
        except routing.RoutingError as exc:
            return Response(
                {"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        all_stations = stations.load_stations()
        route_stops = corridor.stations_along_route(
            route["geometry"], all_stations, settings.CORRIDOR_MILES
        )

        warnings = []
        try:
            planned, total_cost = optimizer.plan_fuel_stops(
                route_stops,
                route["distance_miles"],
                settings.VEHICLE_RANGE_MILES,
                settings.VEHICLE_MPG,
            )
        except optimizer.InfeasibleRoute as exc:
            planned, total_cost = [], 0.0
            warnings.append(
                f"Route exceeds known fuel coverage around mile {exc.at_mile:.0f}: "
                "no station in the dataset within one tank range. "
                "Fuel plan is unavailable for this route."
            )

        response = {
            "start": {"query": start, **start_geo},
            "finish": {"query": finish, **finish_geo},
            "route": {
                "distance_miles": round(route["distance_miles"], 1),
                "duration_hours": round(route["duration_hours"], 1),
                "geometry": {
                    "type": "LineString",
                    "coordinates": route["geometry"],
                },
            },
            "vehicle": {
                "range_miles": settings.VEHICLE_RANGE_MILES,
                "mpg": settings.VEHICLE_MPG,
                "tank_gallons": settings.VEHICLE_TANK_GALLONS,
            },
            "fuel_stops": [
                {
                    "name": s.station.name,
                    "address": s.station.address,
                    "city": s.station.city,
                    "state": s.station.state,
                    "lat": s.station.lat,
                    "lon": s.station.lon,
                    "mile_marker": round(s.mile_marker, 1),
                    "price_per_gallon": round(s.station.price, 3),
                    "gallons_purchased": round(s.gallons, 1),
                    "cost": round(s.cost, 2),
                }
                for s in planned
            ],
            "total_gallons": round(sum(s.gallons for s in planned), 1),
            "total_fuel_cost": round(total_cost, 2),
            "warnings": warnings,
            "meta": {
                "routing_api_calls": 1,
                "corridor_stations_considered": len(route_stops),
                "cache_hit": False,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 1),
            },
        }
        status_code = status.HTTP_200_OK if not warnings else status.HTTP_200_OK
        cache.set(cache_key, response, settings.ROUTE_CACHE_SECONDS)
        return Response(response, status=status_code)
