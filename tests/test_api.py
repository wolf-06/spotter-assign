from unittest.mock import patch

from django.core.cache import cache
from django.test import SimpleTestCase

from routes.services.stations import Station

FAKE_GEOMETRY = [[-74.0, 40.7], [-75.0, 40.0], [-76.0, 39.0]]
FAKE_ROUTE = {"distance_miles": 95.0, "duration_hours": 1.8, "geometry": FAKE_GEOMETRY}


def fake_geocode(query):
    return {"lat": 40.7, "lon": -74.0, "display_name": query}


class RouteApiTests(SimpleTestCase):
    def setUp(self):
        cache.clear()

    def test_missing_params_400(self):
        resp = self.client.post("/api/route/", {}, content_type="application/json")
        self.assertEqual(resp.status_code, 400)

    @patch("routes.services.stations.load_stations")
    @patch("routes.views.routing.get_route", return_value=dict(FAKE_ROUTE))
    @patch("routes.views.geocoding.geocode_place", side_effect=fake_geocode)
    def test_happy_path_short_route(self, _geo, _route, mock_stations):
        mock_stations.return_value = [
            Station("1", "Test Stop", "I-95", "Newark", "NJ", 3.10, 40.5, -74.4, "address")
        ]
        resp = self.client.post(
            "/api/route/",
            {"start": "New York, NY", "finish": "Philadelphia, PA"},
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["fuel_stops"], [])  # 95 mi < 500 mi range
        self.assertEqual(data["total_fuel_cost"], 0.0)
        self.assertEqual(data["route"]["distance_miles"], 95.0)
        self.assertEqual(data["meta"]["routing_api_calls"], 1)

    @patch("routes.services.stations.load_stations")
    @patch("routes.views.routing.get_route", return_value=dict(FAKE_ROUTE))
    @patch("routes.views.geocoding.geocode_place", side_effect=fake_geocode)
    def test_response_is_cached(self, _geo, _route, mock_stations):
        mock_stations.return_value = []
        self.client.get("/api/route/?start=A&finish=B")
        resp = self.client.get("/api/route/?start=A&finish=B")
        self.assertTrue(resp.json()["meta"]["cache_hit"])

    @patch("routes.views.geocoding.geocode_place")
    def test_unresolvable_location_400(self, mock_geo):
        from routes.services.geocoding import GeocodeError

        mock_geo.side_effect = GeocodeError("could not resolve location: 'Nowhere'")
        resp = self.client.get("/api/route/?start=Nowhere&finish=Somewhere")
        self.assertEqual(resp.status_code, 400)


if __name__ == "__main__":
    import unittest

    unittest.main()
