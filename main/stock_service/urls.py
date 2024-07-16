from django.urls import path, include
from stock_service.views import interactive_brokers, metatrader

urlpatterns = [
    path("interactive_brokers/", interactive_brokers, name="interactive_brokers"),
    path("metatrader/", metatrader, name="metatrader"),
    path("accounts/", include("django.contrib.auth.urls")),
]
app_name = "stock_service"
