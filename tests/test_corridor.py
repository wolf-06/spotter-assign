import unittest

from routes.services.corridor import haversine_mi, stations_along_route
from routes.services.stations import Station


def station(opis_id, lat, lon):
    return Station(
        opis_id=opis_id, name=opis_id, address="", city="", state="",
        price=3.0, lat=lat, lon=lon, geocode_quality="address",
    )


class CorridorTests(unittest.TestCase):
    # Straight east-west route along the equator: 0,0 -> 0,10 (10 degrees).
    GEOMETRY = [[lon, 0.0] for lon in [i / 10 for i in range(101)]]

    def test_station_on_route_is_found(self):
        stops = stations_along_route(self.GEOMETRY, [station("on", 0.01, 5.0)], 10.0)
        self.assertEqual(len(stops), 1)
        self.assertAlmostEqual(stops[0].mile_marker, haversine_mi(0, 5.0, 0, 0), delta=10.0)

    def test_station_far_away_is_excluded(self):
        stops = stations_along_route(self.GEOMETRY, [station("far", 5.0, 5.0)], 10.0)
        self.assertEqual(stops, [])

    def test_stops_sorted_by_mile_marker(self):
        stations = [station("b", 0.0, 8.0), station("a", 0.0, 2.0)]
        stops = stations_along_route(self.GEOMETRY, stations, 10.0)
        self.assertEqual([s.station.opis_id for s in stops], ["a", "b"])


if __name__ == "__main__":
    unittest.main()
