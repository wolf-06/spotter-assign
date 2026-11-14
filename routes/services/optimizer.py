"""Cheapest-fuel-stop planner.

Vehicle: fixed tank (500 mi range / 10 mpg = 50 gal), starts full at the
origin; origin fuel is free. Every other gallon is bought at a station's
retail price.

Greedy (provably optimal for a fixed tank and linear consumption):
  1. From the current position, drive to the *cheapest* station reachable
     with the fuel on board - passing pricier stations can never pay off,
     because any fuel bought there costs less at the cheapest one.
  2. At that station, look ahead one full tank of range:
       - if a cheaper station is within range, buy just enough to reach the
         nearest cheaper station (or the destination, if closer);
       - otherwise fill up completely - everything ahead costs more, so
         carry as much of this relatively cheap fuel as possible.
  3. Repeat until the destination is in range.

Runs in roughly O(n * k) where k is the number of stations inside one tank
range - trivially fast for corridor-sized inputs.
"""
from dataclasses import dataclass

from .corridor import RouteStop


class InfeasibleRoute(Exception):
    """A stretch of road longer than one tank range has no known station."""

    def __init__(self, at_mile: float):
        self.at_mile = at_mile
        super().__init__(f"no fuel station within range at mile {at_mile:.1f}")


@dataclass
class PlannedStop:
    station: object  # Station
    mile_marker: float
    gallons: float
    cost: float


def plan_fuel_stops(
    route_stops: list[RouteStop],
    total_miles: float,
    range_miles: float,
    mpg: float,
) -> tuple[list[PlannedStop], float]:
    """Return (planned stops, total fuel cost)."""
    tank = range_miles / mpg
    fuel = tank  # start full; origin fuel is free
    pos = 0.0
    planned: list[PlannedStop] = []

    # Only stations strictly ahead of the current position are candidates.
    upcoming = [s for s in route_stops if s.mile_marker > 1e-9]
    idx = 0

    while pos + fuel * mpg < total_miles - 1e-9:
        reach = pos + fuel * mpg
        window = []
        j = idx
        while j < len(upcoming) and upcoming[j].mile_marker <= reach + 1e-9:
            window.append((j, upcoming[j]))
            j += 1
        if not window:
            raise InfeasibleRoute(reach)

        # Cheapest reachable station; farthest one wins ties.
        target_j, target = min(
            window, key=lambda item: (item[1].station.price, -item[1].mile_marker)
        )

        dist = target.mile_marker - pos
        fuel -= dist / mpg
        pos = target.mile_marker
        idx = target_j + 1

        # Look ahead one full tank for a cheaper station.
        horizon = pos + range_miles
        next_cheaper_mile = None
        for s in upcoming[idx:]:
            if s.mile_marker > horizon + 1e-9:
                break
            if s.station.price < target.station.price:
                next_cheaper_mile = s.mile_marker
                break

        # Buy enough to reach the next cheaper station or the destination;
        # fill the tank when neither is in range (everything ahead costs more).
        if next_cheaper_mile is not None:
            need_to = next_cheaper_mile
        elif total_miles <= horizon:
            need_to = total_miles
        else:
            need_to = horizon

        gallons = max(0.0, (need_to - pos) / mpg - fuel)
        fuel += gallons
        if gallons <= 1e-9:
            # Already carrying enough to reach the next cheaper station (or the
            # destination) - passing this stop changes nothing, so skip it.
            continue
        planned.append(
            PlannedStop(
                station=target.station,
                mile_marker=pos,
                gallons=gallons,
                cost=gallons * target.station.price,
            )
        )

    total_cost = sum(s.cost for s in planned)
    return planned, total_cost
