"""One-time offline geocoding of the assessment fuel CSV.

The provided fuel CSV has no coordinates. This script regenerates
data/fuel_stations_geocoded.csv:

  1. US Census batch geocoder (free, no key, one request for all rows) on the
     full street address.
  2. City/state centroid fallback from the GeoNames US/CA dumps
     (download.geonames.org/export/dump/{US,CA}.zip).

The results are committed to the repo, so running this is NOT part of setup -
it exists for reproducibility. Requires: requests, and the GeoNames dumps
(US.txt, CA.txt) placed next to this script.
"""
import csv
import io
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "fuel-prices-for-be-assessment.csv"
TARGET = ROOT / "data" / "fuel_stations_geocoded.csv"
CENSUS_BATCH_URL = "https://geocoding.geo.census.gov/geocoder/locations/addressbatch"


def norm(s: str) -> str:
    s = s.lower().strip().replace("'", "").replace(".", "").replace("-", " ")
    return re.sub(r"\s+", " ", s)


def variants(c: str):
    yield c
    yield c.replace(" ", "")
    for a, b in (("saint ", "st "), ("st ", "saint "), ("mount ", "mt "),
                 ("fort ", "ft "), ("s ", "south "), ("n ", "north ")):
        if c.startswith(a):
            yield b + c[len(a):]


def load_geonames(paths):
    cities = {}
    for path in paths:
        for line in open(path, encoding="utf-8"):
            p = line.rstrip("\n").split("\t")
            if len(p) < 15 or p[6] != "P":
                continue
            pop = int(p[14] or 0)
            for name in (p[1], p[2]):
                key = (norm(name), p[10])
                if key not in cities or pop > cities[key][2]:
                    cities[key] = (float(p[4]), float(p[5]), pop)
    return cities


def main():
    rows = list(csv.DictReader(open(SOURCE, newline="", encoding="utf-8")))

    buf = io.StringIO()
    writer = csv.writer(buf)
    for r in rows:
        writer.writerow([r["OPIS Truckstop ID"], r["Address"], r["City"], r["State"], ""])
    resp = requests.post(
        CENSUS_BATCH_URL,
        files={"addressFile": ("input.csv", buf.getvalue())},
        data={"benchmark": "Public_AR_Current"},
        timeout=300,
    )
    resp.raise_for_status()
    census = {}
    for r in csv.reader(io.StringIO(resp.text)):
        if len(r) > 5 and r[2] in ("Match", "Tie") and r[5]:
            lon, lat = r[5].split(",")
            census[r[0]] = (float(lat), float(lon))

    here = Path(__file__).resolve().parent
    cities = load_geonames([here / "US.txt", here / "CA.txt"])

    seen, out, unmatched = set(), [], 0
    for r in rows:
        oid = r["OPIS Truckstop ID"]
        if oid in seen:
            continue
        seen.add(oid)
        lat = lon = None
        quality = ""
        if oid in census:
            lat, lon = census[oid]
            quality = "address"
        else:
            for v in variants(norm(r["City"])):
                hit = cities.get((v, r["State"]))
                if hit:
                    lat, lon = hit[0], hit[1]
                    quality = "city_centroid"
                    break
        if lat is None:
            unmatched += 1
        out.append({
            "opis_id": oid,
            "name": r["Truckstop Name"].strip(),
            "address": r["Address"].strip(),
            "city": r["City"].strip(),
            "state": r["State"],
            "retail_price": r["Retail Price"],
            "lat": f"{lat:.6f}" if lat is not None else "",
            "lon": f"{lon:.6f}" if lon is not None else "",
            "geocode_quality": quality,
        })

    with open(TARGET, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    print(f"wrote {len(out)} stations ({unmatched} unmatched) to {TARGET}")


if __name__ == "__main__":
    sys.exit(main())
