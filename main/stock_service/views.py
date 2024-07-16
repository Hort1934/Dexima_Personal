from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from source.decorators import set_user_language
from stock_service.models import StockTradingPair

trading_pairs = StockTradingPair.objects.all()


@set_user_language
@login_required
def stock_index(request):
    # load_stock_data()
    selected_pair = ""
    if request.method == "POST":
        if "stock" in request.POST:
            selected_pair_id = request.POST.get("stock")
            selected_pair = StockTradingPair.objects.get(pk=selected_pair_id)
            request.user.selected_pair = selected_pair
            # TODO make a lists of available for each broker trading pairs if
            #  client choose some pair look for it in this lists
            # EXAMPLE binance : BTC/BUSD, ETH/USDT/, XRP/USDT, bybit: LTC/USDT,
            # DOT/USDT, BTC/USDT kukoin: SHIB/USDT, BTC/USDT
            # if selected_pair in binance add button binance, if in bybit add
            # button bybit, if in kukoin add button kukoin

        selected = (
            hasattr(request.user, "selected_pair")
            and request.user.selected_pair is not None
        )
        return render(
            request,
            "stock_service/stock_index.html",
            {
                "tradingpair": trading_pairs,
                "selected": selected,
                "selected_pair": selected_pair,
            },
        )
    elif request.method == "GET":
        return render(
            request, "stock_service/stock_index.html", {"tradingpair": trading_pairs}
        )
    return render(request, "stock_service/stock_index.html")


@set_user_language
@login_required
def interactive_brokers(request):
    return render(request, "stock_service/interactive_brokers.html")


@set_user_language
@login_required
def metatrader(request):
    return render(request, "stock_service/metatrader.html")
