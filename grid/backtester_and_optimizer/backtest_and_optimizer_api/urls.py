from django.urls import path
from backtest_and_optimizer_api.views import backtest, grid_backtest, grid_optimize

urlpatterns = [
    path("backtest/", backtest, name="backtest"),
    path("grid_backtest/", grid_backtest, name="grid_backtest"),
    path("grid_optimize/", grid_optimize, name="grid_optimize"),
]
app_name = "backtest_and_optimizer_api"
