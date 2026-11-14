"""Validate (and report on) the geocoded fuel station data.

The geocoded CSV is committed to the repo, so there is nothing to run at
setup time - this command is a sanity check and a data summary. To regenerate
coordinates from scratch, see scripts/geocode_stations.py.
"""
from django.core.management.base import BaseCommand

from routes.services import stations


class Command(BaseCommand):
    help = "Load the geocoded fuel price CSV and print a data summary."

    def handle(self, *args, **options):
        stations.reset_cache()
        data = stations.load_stations()
        by_quality = {}
        by_state = {}
        for s in data:
            by_quality[s.geocode_quality] = by_quality.get(s.geocode_quality, 0) + 1
            by_state[s.state] = by_state.get(s.state, 0) + 1
        self.stdout.write(self.style.SUCCESS(f"Loaded {len(data)} stations"))
        for quality, count in sorted(by_quality.items()):
            self.stdout.write(f"  geocode={quality}: {count}")
        self.stdout.write(f"  states/territories: {len(by_state)}")
        prices = [s.price for s in data]
        self.stdout.write(
            f"  price range: ${min(prices):.3f} - ${max(prices):.3f} per gallon"
        )
