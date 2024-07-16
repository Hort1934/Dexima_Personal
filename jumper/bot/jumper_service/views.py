import time
from multiprocessing import Process, Event
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from source.g_vers import Bot
from source.utils import get_user_bybit_credentials, get_user_username
from source import Fields

processes = []


class StopBotView(APIView):

    @staticmethod
    def post(request, *args, **kwargs):
        try:
            # data = request.stream.GET
            data = request.data
            bot_id = int(data.get("bot_id"))
            # close_positions = data.get("close_positions", "").lower() == 'true'

            # if close_positions:
            #     user_id = data.get("user_id")
            #     symbol = str(data.get("symbol"))
            #     side = str(data.get("side"))
            #     quantity = float(data.get("quantity"))
            #     api_key, secret_key = get_user_bybit_credentials(user_id)
            #     close_user_position_and_orders(api_key=api_key, api_secret=secret_key, symbol=symbol, side=side,
            #                                    quantity=quantity)
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
        data = request.data
        try:
            user_id = data.get("user_id")
            bot_id = int(data.get("bot_id"))
            symbol = data.get("symbol")
            fields = Fields(
                long_entry_sum_in_dollars=int(data.get("long_entry_sum_in_dollars")),
                short_entry_sum_in_dollars=int(data.get("short_entry_sum_in_dollars")),
                long_take_profit_percent=int(data.get("long_take_profit_percent")),
                long_stop_loss_percent=int(data.get("long_stop_loss_percent")),
                short_take_profit_percent=int(data.get("short_take_profit_percent")),
                short_stop_loss_percent=int(data.get("short_stop_loss_percent")),
                price_difference_long_entry=float(
                    data.get("price_difference_long_entry")
                ),
                price_difference_short_entry=float(
                    data.get("price_difference_short_entry")
                ),
                block_long_trade_until=None,
                block_short_trade_until=None,
                long_pause_after_trade_min=int(data.get("long_pause_after_trade_min")),
                short_pause_after_trade_min=int(
                    data.get("short_pause_after_trade_min")
                ),
                order_expiration_by_price_percent_limit=int(
                    data.get("order_expiration_by_price_percent_limit")
                ),
                short_period=int(data.get("short_period")),
                long_period=int(data.get("long_period")),
                LEVERAGE=int(data.get("LEVERAGE")),
                long_trailing_stop=float(data.get("long_trailing_stop")),
                short_trailing_stop=float(data.get("short_trailing_stop")),
            )
            try:
                api_key, secret_key = get_user_bybit_credentials(user_id=user_id)
            except:
                raise "Api or secret not set"
            username = get_user_username(user_id)
            print(f"Jumper bot for user: {username}, symbol: {symbol}, started!")

            # Запускаем бота в отдельном процессе
            stop_flag_1 = Event()  # Используем Event вместо Value
            p = Process(
                target=run_bot,
                args=(bot_id, api_key, secret_key, fields, symbol, stop_flag_1),
            )
            processes.append({"process": p, "stop_flag": stop_flag_1, "name": bot_id})
            p.start()
            return Response({"status": "success"}, status=status.HTTP_200_OK)
        except Exception as ex:
            print(ex)
            return Response({"status": "error", "message": str(ex)})


def run_bot(
    bot_id: int, api_key: str, secret_key: str, fields: dict, symbol: str, stop_flag
):
    bot = Bot(
        fields=fields, apiKey=api_key, secret=secret_key, symbol=symbol, test_mode=False
    )
    while not stop_flag.is_set():
        bot.run()
        # try:
        #     bot.run()
        # except Exception as ex:
        #     print(ex)
