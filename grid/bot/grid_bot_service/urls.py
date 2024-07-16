from django.urls import path
from grid_bot_service.views import StartBotView, StopBotView

urlpatterns = [
    path("start_grid_bot/", StartBotView.as_view(), name="start_grid_bot"),
    path("stop_grid_bot/", StopBotView.as_view(), name="stop_grid_bot"),
]
app_name = "grid_bot_service"
