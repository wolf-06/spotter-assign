from django.urls import include, path

urlpatterns = [
    path("api/", include("routes.urls")),
    path("", include("routes.map_urls")),
]
