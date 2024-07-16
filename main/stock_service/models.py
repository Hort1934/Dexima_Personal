from django.db import models


class StockTradingPair(models.Model):
    base_currency = models.CharField(max_length=10)

    def __str__(self):
        return f"{self.base_currency}"
