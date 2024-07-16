import asyncio

import time


from multiprocessing import Process, Event

from rest_framework.views import APIView

from rest_framework.response import Response

from rest_framework import status

from source.grid_project.src.__main__ import main

from source.utils import (
    get_user_bybit_credentials,
    get_user_username,
    close_user_position_and_orders,
)


processes = []


class StopBotView(APIView):

    @staticmethod
    def post(request, *args, **kwargs):

        try:

            # data = request.stream.GET

            data = request.data

            bot_id = int(data.get("bot_id"))

            close_positions = data.get("close_positions", "").lower() == "true"

            if close_positions:

                user_id = data.get("user_id")

                symbol = str(data.get("symbol"))

                side = str(data.get("side"))

                quantity = float(data.get("quantity"))

                api_key, secret_key = get_user_bybit_credentials(user_id)

                close_user_position_and_orders(
                    api_key=api_key,
                    api_secret=secret_key,
                    symbol=symbol,
                    side=side,
                    quantity=quantity,
                )

            # Находим процесс и флаг в списке по bot_id и устанавливаем флаг

            for process_info in processes:

                if int(process_info["name"]) == bot_id:

                    process_info["stop_flag"].set()

                    time.sleep(3)

                if process_info["stop_flag"].is_set():

                    process_info["process"].terminate()

                    process_info["process"].join()

                    processes.remove(process_info)

            print(f"Processes after close:\n{processes}")

            return Response({"status": "success"}, status=status.HTTP_200_OK)

        except Exception as ex:

            return Response(
                {"status": "error", "message": str(ex)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class StartBotView(APIView):

    @staticmethod
    def post(request, *args, **kwargs):

        params = {}

        try:

            # data = request.stream.GET

            data = request.data

            user_id = data.get("user_id")

            bot_id = int(data.get("bot_id"))

            params["symbol"] = data.get("symbol")

            params["available_balance"] = data.get("available_balance")

            params["leverage"] = data.get("leverage")

            params["num_of_grids"] = data.get("num_of_grids")

            params["timeframe"] = data.get("timeframe")

            params["price_range"] = data.get("price_range")

            params["activation_trigger_in_percent"] = data.get(
                "activation_trigger_in_percent"
            )

            params["distribution_of_grid_lines"] = data.get(
                "distribution_of_grid_lines"
            )

            params["line_disbalance_direction"] = data.get("line_disbalance_direction")

            params["short_stop_loss_in_percent"] = data.get(
                "short_stop_loss_in_percent"
            )

            params["long_stop_loss_in_percent"] = data.get("long_stop_loss_in_percent")

            params["grid_disbalance_direction"] = data.get("grid_disbalance_direction")

            params["trend_period_timeframe"] = data.get("trend_period_timeframe")

            params["trend_period"] = data.get("trend_period")

            # api_key, secret_key = get_user_binance_credentials(user_id)

            api_key, secret_key = get_user_bybit_credentials(user_id=user_id)

            # getting username

            username = get_user_username(user_id)

            print(
                f"Grid bot for user: {username}, symbol: {params['symbol']}, started!"
            )

            # Запускаем бота в отдельном процессе

            stop_flag_1 = Event()  # Используем Event вместо Value

            p = Process(
                target=run_bot, args=(bot_id, api_key, secret_key, params, stop_flag_1)
            )

            processes.append({"process": p, "stop_flag": stop_flag_1, "name": bot_id})

            p.start()

            return Response({"status": "success"}, status=status.HTTP_200_OK)

        except Exception as ex:

            print(ex)

            return Response(
                {"status": "error", "message": str(ex)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


def run_bot(bot_id: int, api_key: str, secret_key: str, params: dict, stop_flag):

    asyncio.run(
        main(
            bot_id=bot_id,
            api_key=api_key,
            secret_key=secret_key,
            params=params,
            stop_flag=stop_flag,
        )
    )
