import requests
import datetime
import json

from rest_framework.decorators import api_view

from source.py_version.g_optimizator import Fields
from source.py_version.db import Database, engine
from source.py_version.g_backtester import Backter
from django.http import JsonResponse

from source.py_version.g_optimizator import Optimizer
from source.src.utils import get_custom_ranges

connection = engine.connect()


@api_view(["POST"])
def jumper_backtest(request):
    try:
        if request.method == "POST":

            data = request.data
            #  ["1s", "1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"]
            leverage = float(data.get("leverage"))
            fields = Fields(
                long_entry_sum_in_dollars=float(data.get("long_entry_sum_in_dollars")),
                short_entry_sum_in_dollars=float(data.get("short_entry_sum_in_dollars")),
                long_take_profit_percent=float(data.get("long_take_profit_percent")),
                long_stop_loss_percent=float(data.get("long_stop_loss_percent")),
                short_take_profit_percent=float(data.get("short_take_profit_percent")),
                short_stop_loss_percent=float(data.get("short_stop_loss_percent")),
                price_difference_long_entry=float(data.get("price_difference_long_entry")),
                price_difference_short_entry=float(
                    data.get("price_difference_short_entry")
                ),
                block_long_trade_until=data.get("block_long_trade_until"),
                block_short_trade_until=data.get("block_short_trade_until"),
                long_pause_after_trade_min=float(data.get("long_pause_after_trade_min")),
                short_pause_after_trade_min=float(data.get("short_pause_after_trade_min")),
                order_expiration_by_price_percent_limit=float(
                    data.get("order_expiration_by_price_percent_limit")
                ),
                short_period=float(data.get("short_period")),
                long_period=float(data.get("long_period")),
                LEVERAGE=leverage,
                long_trailing_stop=float(data.get("long_trailing_stop")),
                short_trailing_stop=float(data.get("short_trailing_stop")),
            )
            if fields.block_long_trade_until is not None:
                fields.block_long_trade_until = float(fields.block_long_trade_until)

            if fields.block_short_trade_until is not None:
                fields.block_short_trade_until = float(fields.block_short_trade_until)
            available_balance = float(data.get("available_balance"))
            timeframe = str(data.get("timeframe"))
            symbol = str(data.get("symbol"))
            from_start = str(data.get("from"))
            to_start = str(data.get("to"))
            original_from_obj = datetime.datetime.strptime(from_start, "%d-%m-%Y")
            from_ = original_from_obj.strftime("%Y-%m-%d")
            original_to_obj = datetime.datetime.strptime(to_start, "%d-%m-%Y")
            to = original_to_obj.strftime("%Y-%m-%d")
            db = Database(conn=connection)
            data = db.get_historical_data(
                exchange="bybit",
                type_="futures",
                symbol=symbol,
                timeframe=timeframe,
                from_=from_,
                to=to,
            )
            # data = get_data(from_str="2023-11-03", to_str="2023-11-10")
            # data = get_data(symbol, timeframe, from_, to)

            b = Backter(data=data, fields=fields, available_balance=available_balance)
            trades = b.run()

            total_pnl = 0
            longs = 0
            shorts = 0
            for trade in trades:
                if "pnl" in trade:
                    total_pnl += trade["pnl"]
                    if trade["side"] == "buy":
                        longs += 1
                    elif trade["side"] == "sell":
                        shorts += 1

            dates = from_start + "-" + to_start
            result_for_table = {
                "STRATEGY": "JUMPER",
                "ASSET": symbol,
                "DATES": dates,
                "INVESTMENT": round(b.start_capital - total_pnl, 0),
                "END BALANCE": round(b.start_capital, 2),
                "PROFIT": round(total_pnl, 2),
                "TOTAL TRADES": len(b.trades),
                "LONG TRADES": longs,
                "SHORT TRADES": shorts,
                "LEVERAGE": fields.LEVERAGE,
                "TIMEFRAME": timeframe,
                "AMOUNT FOR LONG": fields.long_entry_sum_in_dollars,
                "AMOUNT FOR SHORT": fields.short_entry_sum_in_dollars,
                "LONG TP %": fields.long_take_profit_percent,
                "LONG PERIOD": fields.long_period,
                "LONG SL %": fields.short_take_profit_percent,
                "LONG DIVERGENCE %": fields.price_difference_long_entry,
                "LONG PAUSE MINUTE": fields.long_pause_after_trade_min,
                "LONG TRAILING STOP": fields.long_trailing_stop,
                "SHORT TP %": fields.short_take_profit_percent,
                "SHORT PERIOD": fields.short_period,
                "SHORT PAUSE MINUTE": fields.short_pause_after_trade_min,
                "SHORT SL %": fields.short_stop_loss_percent,
                "SHORT DIVERGENCE %": fields.price_difference_short_entry,
                "SHORT TRAILING STOP": fields.short_trailing_stop,
                "PRICE CHANGE LIMIT %": fields.order_expiration_by_price_percent_limit,
            }
            return JsonResponse(result_for_table)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@api_view(["POST"])
def jumper_optimize(request):
    try:
        if request.method == "POST":
            longs, shorts = 0, 0
            data = request.data

            # 60-DataFromOptimizer
            backtest_and_optimization_id = data.get("backtest_and_optimization_id")
            # 60-DataFromOptimizer

            leverage = int(data.get("leverage"))
            params = json.loads(data.get("data"))
            params['Leverage'] = leverage
            symbol = data.get("symbol")
            # chosen_strategy = json.loads(request.data["data"])["strategyName"]
            available_balance = float(data.get("available_balance"))
            # timeframe = json.loads(request.data["data"])["timeframe"]
            timeframe = str(data.get("timeframe"))
            from_start = data.get("from")
            to_start = data.get("to")
            original_from_obj = datetime.datetime.strptime(from_start, "%d-%m-%Y")
            from_ = original_from_obj.strftime("%Y-%m-%d")
            original_to_obj = datetime.datetime.strptime(to_start, "%d-%m-%Y")
            to = original_to_obj.strftime("%Y-%m-%d")
            db = Database(conn=connection)
            data = db.get_historical_data(
                exchange="bybit",
                type_="futures",
                symbol=symbol,
                timeframe=timeframe,
                from_=from_,
                to=to,
            )
            custom_ranges = get_custom_ranges(params)
            optimizator = Optimizer(
                data, custom_ranges, available_balance=available_balance
            )
            fields = optimizator.execute()
            dates = from_start + "-" + to_start

            for trade in fields["trades"]:
                if trade["side"] == "buy":
                    longs += 1
                else:
                    shorts += 1
            result_for_table = {
                "STRATEGY": "JUMPER",
                "ASSET": symbol,
                "DATES": dates,
                "INVESTMENT": available_balance,
                "END BALANCE": round(fields["start_capital"], 2),
                "PROFIT": round(fields["start_capital"] - available_balance, 2),
                "TOTAL TRADES": len(fields["trades"]),
                "LONG TRADES": longs,
                "SHORT TRADES": shorts,
                "LEVERAGE": fields["fields"].LEVERAGE,
                "SETTINGS": {
                    "TIMEFRAME": timeframe,
                    "AMOUNT FOR LONG": fields["fields"].long_entry_sum_in_dollars,
                    "AMOUNT FOR SHORT": fields["fields"].short_entry_sum_in_dollars,
                    "LONG TP %": fields["fields"].long_take_profit_percent,
                    "LONG PERIOD": fields["fields"].long_period,
                    "LONG SL %": fields["fields"].short_take_profit_percent,
                    "LONG DIVERGENCE %": fields["fields"].price_difference_long_entry,
                    "LONG PAUSE MINUTE": fields["fields"].long_pause_after_trade_min,
                    "LONG TRAILING STOP": fields["fields"].long_trailing_stop,
                    "SHORT TP %": fields["fields"].short_take_profit_percent,
                    "SHORT PERIOD": fields["fields"].short_period,
                    "SHORT PAUSE MINUTE": fields["fields"].short_pause_after_trade_min,
                    "SHORT SL %": fields["fields"].short_stop_loss_percent,
                    "SHORT DIVERGENCE %": fields["fields"].price_difference_short_entry,
                    "SHORT TRAILING STOP": fields["fields"].short_trailing_stop,
                    "PRICE CHANGE LIMIT %": fields[
                        "fields"
                    ].order_expiration_by_price_percent_limit,
                },
            }
            return JsonResponse(result_for_table)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)