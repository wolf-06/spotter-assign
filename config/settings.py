from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# Dev-only key for a coding assessment; override via env in real deployments.
SECRET_KEY = "spotter-assessment-dev-key"
DEBUG = True
ALLOWED_HOSTS = ["*"]

INSTALLED_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.staticfiles",
    "rest_framework",
    "routes",
]

MIDDLEWARE = [
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": []},
    }
]

WSGI_APPLICATION = "config.wsgi.application"

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "spotter-fuel-route",
    }
}

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": [],
}

# --- Assessment domain constants -------------------------------------------
VEHICLE_RANGE_MILES = 500.0   # tank range
VEHICLE_MPG = 10.0            # miles per gallon
VEHICLE_TANK_GALLONS = VEHICLE_RANGE_MILES / VEHICLE_MPG  # 50 gal
CORRIDOR_MILES = 10.0         # max off-route distance for a fuel station

OSRM_BASE_URL = "https://router.project-osrm.org"
NOMINATIM_BASE_URL = "https://nominatim.openstreetmap.org"
GEOCODE_CACHE_SECONDS = 60 * 60 * 24 * 30   # 30 days
ROUTE_CACHE_SECONDS = 60 * 60 * 24          # 24 hours
FUEL_DATA_FILE = BASE_DIR / "data" / "fuel_stations_geocoded.csv"
