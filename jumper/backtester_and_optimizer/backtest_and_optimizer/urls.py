from django.urls import path
from backtest_and_optimizer.views import jumper_backtest, jumper_optimize

urlpatterns = [
    path("jumper_backtest/", jumper_backtest, name="jumper_backtest"),
    path("jumper_optimize/", jumper_optimize, name="jumper_optimize"),
]
app_name = "backtest_and_optimizer_api"
