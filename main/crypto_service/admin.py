from django.contrib import admin
from crypto_service.models import (
    CryptoTradingPair,
    OptimizedStrategies,
    TradingBots,
    BotsStatistic,
)


class YourModelAdmin(admin.ModelAdmin):
    list_display = ("field1", "field2", "field3")


admin.site.register(CryptoTradingPair)
admin.site.register(OptimizedStrategies)
admin.site.register(TradingBots)
admin.site.register(BotsStatistic)
