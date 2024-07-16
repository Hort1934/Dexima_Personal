from django.db import models


class BacktestF1(models.Model):
    chosen_strategy = models.CharField(max_length=255, null=False)
    symbol = models.CharField(max_length=255, null=False)
    days_of_backtest = models.IntegerField()
    just_backtest = models.BooleanField()
    interval_for_backtest = models.FloatField()
    start_balance = models.FloatField()
