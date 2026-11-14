import unittest

from routes.services.corridor import RouteStop
from routes.services.optimizer import InfeasibleRoute, plan_fuel_stops
from routes.services.stations import Station


def make_stop(mile, price, name="S"):
    st = Station(
        opis_id=name, name=name, address="", city="", state="",
        price=price, lat=0.0, lon=0.0, geocode_quality="address",
    )
    return RouteStop(station=st, mile_marker=mile, off_route_miles=0.0)


class OptimizerTests(unittest.TestCase):
    RANGE = 500.0
    MPG = 10.0

    def plan(self, stops, total_miles):
        return plan_fuel_stops(stops, total_miles, self.RANGE, self.MPG)

    def test_short_route_needs_no_stops(self):
        planned, cost = self.plan([make_stop(100, 3.0)], total_miles=400)
        self.assertEqual(planned, [])
        self.assertEqual(cost, 0.0)

    def test_single_stop_full_refill(self):
        # 1000 mi route, one station at mile 500. Start full (free), arrive
        # empty, buy the 50 gal needed for the remaining 500 mi.
        planned, cost = self.plan([make_stop(500, 3.0)], total_miles=1000)
        self.assertEqual(len(planned), 1)
        self.assertAlmostEqual(planned[0].gallons, 50.0, places=3)
        self.assertAlmostEqual(cost, 150.0, places=3)

    def test_skips_pricier_station_for_cheaper_one(self):
        stops = [make_stop(100, 3.50, "pricey"), make_stop(400, 2.90, "cheap")]
        planned, cost = self.plan(stops, total_miles=800)
        # Arrive at the mile-400 stop with 10 gal left; buy 30 gal for the rest.
        self.assertEqual([s.station.name for s in planned], ["cheap"])
        self.assertAlmostEqual(planned[0].gallons, 30.0, places=3)
        self.assertAlmostEqual(cost, 87.0, places=3)

    def test_buys_just_enough_to_reach_cheaper_station(self):
        # Station A (mile 400, $3.00), cheaper B (mile 800, $2.50).
        # At A (arrive with 10 gal) buy only the 30 gal needed to reach B;
        # at B (empty) buy the remaining 30 gal.
        stops = [make_stop(400, 3.00, "A"), make_stop(800, 2.50, "B")]
        planned, cost = self.plan(stops, total_miles=1100)
        self.assertEqual([s.station.name for s in planned], ["A", "B"])
        self.assertAlmostEqual(planned[0].gallons, 30.0, places=3)
        self.assertAlmostEqual(planned[1].gallons, 30.0, places=3)
        self.assertAlmostEqual(cost, 30 * 3.00 + 30 * 2.50, places=3)

    def test_fills_full_when_only_pricier_ahead(self):
        # Cheap at mile 450 ($2.80), pricey at 900 ($3.50). Fill full at the
        # cheap one, then buy the remainder at the pricey one.
        stops = [make_stop(450, 2.80, "cheap"), make_stop(900, 3.50, "pricey")]
        planned, cost = self.plan(stops, total_miles=1200)
        self.assertEqual([s.station.name for s in planned], ["cheap", "pricey"])
        # Cheap stop: arrive with 5 gal, fill to full = 45 gal.
        self.assertAlmostEqual(planned[0].gallons, 45.0, places=3)
        # Pricey stop: arrive with 5 gal, buy 25 gal for the last 300 mi.
        self.assertAlmostEqual(planned[1].gallons, 25.0, places=3)
        self.assertAlmostEqual(cost, 45 * 2.80 + 25 * 3.50, places=3)

    def test_infeasible_gap_raises(self):
        with self.assertRaises(InfeasibleRoute):
            self.plan([make_stop(600, 3.0)], total_miles=1300)


if __name__ == "__main__":
    unittest.main()
