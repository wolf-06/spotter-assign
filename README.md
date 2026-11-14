# Fuel Route API - Spotter Backend Assessment

A Django API that plans the cheapest fuel stops along a US driving route.

Given a start and finish location (anywhere in the USA), it returns the route
geometry, the optimal fuel stops from the provided OPIS truck-stop price file,
and the total fuel cost for a vehicle with a 500-mile range at 10 mpg.

Built with Django 5.2 + Django REST framework. Routing by OSRM (free, one
call per route), geocoding by Nominatim (free, cached). No API keys required.

## Quick start

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate       # Django internal tables only; fuel data ships in data/
python manage.py runserver
```

Everything needed is committed, including the geocoded station data - there is
no data setup step. Then:

```bash
curl -X POST http://localhost:8000/api/route/ \
  -H 'Content-Type: application/json' \
  -d '{"start": "New York, NY", "finish": "Los Angeles, CA"}'
```

or open http://localhost:8000/map/ for the same result drawn on a map.

Run the tests with `python manage.py test tests` and the data sanity check
with `python manage.py load_fuel_data`.

## API

`POST /api/route/` (also `GET /api/route/?start=...&finish=...`)

```json
{ "start": "New York, NY", "finish": "Los Angeles, CA" }
```

Response:

```json
{
  "route": {
    "distance_miles": 2789.4,
    "duration_hours": 41.2,
    "geometry": { "type": "LineString", "coordinates": [[-74.0, 40.7], "..."] }
  },
  "fuel_stops": [
    {
      "name": "PILOT #123",
      "address": "I-70, Exit 200", "city": "...", "state": "KS",
      "lat": 39.0, "lon": -98.3,
      "mile_marker": 480.2,
      "price_per_gallon": 2.89,
      "gallons_purchased": 47.9,
      "cost": 138.43
    }
  ],
  "total_gallons": 278.9,
  "total_fuel_cost": 812.35,
  "vehicle": { "range_miles": 500, "mpg": 10, "tank_gallons": 50 },
  "warnings": [],
  "meta": { "routing_api_calls": 1, "cache_hit": false, "elapsed_ms": 240 }
}
```

Errors: `400` for missing/unresolvable/non-US locations, `503` if the routing
provider is down. A route with a >500-mile stretch without any station in the
dataset still returns `200` with the route and a `warnings` entry.

## How it works

1. **Geocode endpoints** - Nominatim resolves start/finish (US only). Results
   are cached for 30 days, so repeated requests make zero geocoding calls.
2. **Route** - one OSRM `/route/v1/driving` call with full GeoJSON geometry.
3. **Corridor match** - stations within 10 miles of the polyline become
   candidates, each tagged with a mile marker (distance along the route).
   A lat/lon grid index keeps this at well under 50 ms for ~6.7k stations.
4. **Optimize** - cheapest-fuel greedy (below).
5. **Cache** - the whole response is cached 24 h keyed on the normalized
   start/finish, so repeats answer in single-digit milliseconds.

### The fuel-stop optimizer

The vehicle has a 50-gallon tank (500 mi at 10 mpg) and starts full; origin
fuel is free. The planner then applies the classic cheapest-gas greedy, which
is provably optimal for a fixed tank and linear consumption:

- Drive to the cheapest station reachable with the fuel on board. Passing
  pricier stations never pays: anything bought there is cheaper at the
  cheapest one.
- At each stop, look ahead one tank of range. If a cheaper station is in
  range, buy just enough to reach it (or the destination). Otherwise fill the
  tank - everything ahead costs more, so carry as much cheap fuel as possible.

## Data notes

The provided CSV (`data/fuel-prices-for-be-assessment.csv`) has **no
coordinates** - only name/address/city/state/price. It also contains 1,413
duplicate OPIS IDs (name variants of the same truck stop), which are deduped
to 6,738 unique stations.

Coordinates were produced once, offline, by `scripts/geocode_stations.py`:

- US Census batch geocoder (free, no key) on the full street address -
  these are mostly highway-exit intersections, so exact matches are rare.
- Fallback: city/state centroid from the GeoNames US/CA dumps.

Coverage: 6,723 of 6,738 stations geocoded (99.8%); the 15 unresolved rows
(obscure place names) are skipped at load time. Most stations carry
city-centroid coordinates, which is accurate enough for 10-mile corridor
matching at 500-mile planning granularity - this is the main accuracy
limitation and is called out here deliberately. The geocoded results are
committed in `data/fuel_stations_geocoded.csv`; the script is only needed to
reproduce them.

## Assumptions & limitations

- The vehicle starts with a full tank; fuel at the origin is not charged.
- OPIS truck-stop prices are treated as the vehicle's fuel price.
- A station is usable if within 10 miles of the route (`CORRIDOR_MILES` in
  `config/settings.py`); the small off-route detour is not added to mileage.
- Mile markers come from the nearest sampled route point (~1-2 mi precision).
- Caches are in-process (`locmem`); swap in Redis for multi-process serving.

## Project layout

```
config/            Django project
routes/            API app: views, urls
routes/services/   geocoding.py, routing.py, corridor.py, optimizer.py, stations.py
routes/management/commands/load_fuel_data.py   data sanity check
routes/templates/routes/map.html               Leaflet demo map
data/              source CSV + geocoded stations CSV
scripts/geocode_stations.py                    one-time geocoding regeneration
tests/             optimizer, corridor, and API tests (external APIs mocked)
```
