from django.urls import path
from django.views.generic import TemplateView

urlpatterns = [
    path("map/", TemplateView.as_view(template_name="routes/map.html"), name="route-map"),
]
