import ast

import asyncio
import requests

import json


from django.http import JsonResponse

from rest_framework.decorators import api_view

from source.backtester_rsi.optimizer_n2 import backtester_rsi

from source import start_grid_bot_backtest, start_grid_bot_optimize, process_dict

from source.grid_project.src.common.strategy.expo_grid import ExpoGridStrategySettings


@api_view(["POST"])
def backtest(request):

    if request.method == "POST":

        data = request.data

        # serializer = BacktestF1(data=data)

        result = backtester_rsi(
            chosen_strategy=str(data.get("chosen_strategy")),
            symbol=str(data.get("symbol")),
            days_of_backtest=int(data.get("days_of_backtest")),
            just_backtest=ast.literal_eval(data.get("just_backtest")),
            interval_for_backtest=float(data.get("interval_for_backtest")),
            start_balance=int(data.get("start_balance")),
        )

        return JsonResponse(result)


@api_view(["POST"])
def grid_optimize(request):
    try:
        if request.method == "POST":

            data = request.data

            # 60-DataFromOptimizer
            backtest_and_optimization_id = data.get("backtest_and_optimization_id")
            # 60-DataFromOptimizer

            symbol = data.get("symbol")

            leverage = data.get("leverage")

            json_data = json.loads(data["data"])

            chosen_strategy = json_data["data"]["strategyName"]

            available_balance = data.get("available_balance")

            from_ = data.get("from")

            to = data.get("to")
            json_data = json.loads(data.get("data"))
            params = json_data["data"]
            result = asyncio.run(
                start_grid_bot_optimize(
                    symbol, leverage, available_balance, from_, to, params, backtest_and_optimization_id
                )
            )
            result["from"] = from_

            result["to"] = to

            result["symbol"] = symbol

            result["leverage"] = leverage

            result["chosen_strategy"] = chosen_strategy

            result = {
                ("ASSET" if key == "symbol" else key): value
                for key, value in result.items()
            }

            result = process_dict(result)

            # 60-DataFromOptimizer
            result_json = json.dumps(result)
            url = 'http://backend-app/update_optimization_data/'
            iterations_data = {
                'backtest_and_optimization_id': backtest_and_optimization_id,
                'result': result_json,
            }
            response = requests.get(url, params=iterations_data)
            if response.status_code == 200:
                response_result = response.json()
                # print(response_result)
            else:
                print(response.text)

            # 60-DataFromOptimizer

            return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(["POST"])
def grid_backtest(request):
    try:

        if request.method == "POST":

            data = request.data

            chosen_strategy = data.get("strategyName")
            if not chosen_strategy:
                chosen_strategy = data.get("chosen_strategy")

            instance = ExpoGridStrategySettings(
                symbol=data.get("symbol"),
                leverage=int(data.get("leverage")),
                num_of_grids=int(data.get("num_of_grids")),
                available_balance=float(data.get("available_balance")),
                timeframe=data.get("timeframe"),
                price_range=int(data.get("price_range")),
                activation_trigger_in_percent=float(
                    data.get("activation_trigger_in_percent")
                ),
                distribution_of_grid_lines=data.get("distribution_of_grid_lines"),
                line_disbalance_direction=data.get("line_disbalance_direction"),
                short_stop_loss_in_percent=float(data.get("short_stop_loss_in_percent")),
                long_stop_loss_in_percent=float(data.get("long_stop_loss_in_percent")),
                grid_disbalance_direction=data.get("grid_disbalance_direction"),
                trend_period_timeframe=data.get("trend_period_timeframe"),
                trend_period=int(data.get("trend_period")),
            )

            from_ = data.get("from")

            to = data.get("to")

            data = instance.model_dump(exclude={"optimization"})

            x = asyncio.run(start_grid_bot_backtest(instance, from_, to))

            result = {
                **x,
                **data,
                "from": from_,
                "to": to,
                "chosen_strategy": chosen_strategy,
            }

            result = {
                ("ASSET" if key == "symbol" else key): value
                for key, value in result.items()
            }

            result = {
                key.upper().replace("_", " "): (
                    round(value, 2) if isinstance(value, float) else value
                )
                for key, value in result.items()
            }

            result["AVAILABLE BALANCE"] = round(float(x["Available balance"]), 2)
            return JsonResponse(result)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    if request.method == "GET":

        data = request.GET

        # asyncio.run(start_grid_bot_backtest(instance, from_, to))

    """
    http://127.0.0.1:8000/api/backtest_and_optimizer_api/grid_backtest?symbol=BTCUSDT&leverage=5&num_of_grids=10&available_balance=1000&timeframe=1m&price_range=72&activation_trigger_in_percent=1.0&distribution_of_grid_lines=LINEAR&line_disbalance_direction=ASCENDING&short_stop_loss_in_percent=1.0&long_stop_loss_in_percent=1.0&grid_disbalance_direction=ASCENDING&trend_period_timeframe=1h&trend_period=72&from=2024-01-18&to=2024-01-26

    """


"""

    symbol: str

    leverage: Union[int, float]

    num_of_grids: int

    available_balance: float

    timeframe: KlineInterval

    price_range: int

    activation_trigger_in_percent: float

    distribution_of_grid_lines: LineDistribution

    line_disbalance_direction: Sort

    short_stop_loss_in_percent: float

    long_stop_loss_in_percent: float

    grid_disbalance_direction: Sort

    trend_period_timeframe: KlineInterval

    trend_period: int

"""
