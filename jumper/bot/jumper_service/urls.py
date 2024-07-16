from django.urls import path
from jumper_service.views import StartBotView, StopBotView

urlpatterns = [
    path("start_jumper_bot/", StartBotView.as_view(), name="start_jumper_bot"),
    path("stop_jumper_bot/", StopBotView.as_view(), name="stop_jumper_bot"),
]
app_name = "jumper_service"
