from django.db import models
from main_service.models import CustomUser
from django.utils import timezone


class CryptoTradingPair(models.Model):
    trading_pair = models.CharField(max_length=100)
    price = models.FloatField()
    price_change_in_24h = models.FloatField()
    volume_change_in_24h = models.FloatField()


class OptimizedStrategies(models.Model):
    STRATEGY_CHOICES = (
        ("jumper", "jumper"),
        ("expo_grid", "expo_grid"),
        ("tango", "tango"),
    )
    # strategy = models.ForeignKey(TradingBots, on_delete=models.CASCADE, null=True, blank=True)
    strategy = models.CharField(max_length=255, choices=STRATEGY_CHOICES, default='jumper')
    user = models.ForeignKey(
        CustomUser, on_delete=models.CASCADE, null=True, blank=True
    )
    optimized_settings = models.JSONField()
    json_data = models.JSONField()
    # 189
    exchange = models.CharField(max_length=25, default="bybit")


class TradingBots(models.Model):
    statuses = [
        ("stopped", "stopped"),
        ("started", "started"),
        ("inactive", "inactive"),
    ]
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    optimized_strategy = models.ForeignKey(
        OptimizedStrategies, on_delete=models.PROTECT
    )
    strategy_name = models.CharField(max_length=100)
    exchange = models.CharField(max_length=25)
    launch_date = models.DateTimeField(default=timezone.now)
    running_time = models.CharField(max_length=25, default="0 days")
    investment_amount = models.FloatField(default=0)
    leverage = models.IntegerField()
    margin_type = models.CharField(max_length=10)
    trading_pair = models.CharField(max_length=100)
    entry_price = models.FloatField(default=0)
    profit = models.FloatField(default=0)
    approximately_price_year = models.FloatField(default=0)
    status = models.CharField(
        max_length=20,
        choices=statuses,
        default="inactive",
    )
    minimal_investment = models.FloatField(default=0)

    def __str__(self):
        return f"{self.user} {self.strategy_name} {self.id}"


class BotsStatistic(models.Model):
    # strategy = models.ForeignKey(TradingBots, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(CustomUser, on_delete=models.PROTECT)
    trading_bot = models.ForeignKey(TradingBots, on_delete=models.CASCADE)
    price = models.FloatField()
    qty = models.FloatField()
    realized_pnl = models.FloatField()
    quote_qty = models.FloatField()
    commission = models.FloatField()
    open_time = models.DateTimeField(blank=True, null=True)
    close_time = models.DateTimeField(blank=True, null=True)
    # 83-DashboardDetailsBotStatisticsStructureTableValues
    unrealized_pnl = models.FloatField(default=0)
