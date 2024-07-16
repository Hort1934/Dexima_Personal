import asyncio
import base64
import binascii
import datetime
import math
import os
import hashlib
import hmac
import time
import aiohttp
import django
import json
import requests
from pybit.exceptions import InvalidRequestError

from pybit.unified_trading import HTTP
from typing import Union
from time import sleep
from django.shortcuts import get_object_or_404
from django.core.cache import cache
from django.http import JsonResponse

from crypto_service.models import CryptoTradingPair, OptimizedStrategies
from stock_service.models import StockTradingPair
from main_service.models import (
    Strategy,
    BacktestAndOptimizationHistory,
    CustomUser,
    UserStatus,
    BinanceApiCredentials,
)
from binance.client import Client
from requests.exceptions import RequestException
from Crypto.Cipher import AES
from dotenv import load_dotenv
from source import send_signed_default_request, send_signed_bybit_default_request
from config import EXPO_GRID_OPTIMIZATION, EXPO_GRID_BACKTEST, JUMPER_BACKTEST, JUMPER_OPTIMIZATION


from main_service import tasks


load_dotenv()


def get_strategies_from_json():
    with open(os.getcwd() + "/source/strategies.json", "r") as file:
        data = json.load(file)
    return data


async def get_binance_price(symbol):
    async with aiohttp.ClientSession() as session:
        url = f"https://api.binance.com/api/v3/ticker/price?symbol={symbol}"
        async with session.get(url) as response:
            data = await response.json()
            return data.get("price")


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dexima_ats_web_service.settings")
django.setup()


def load_strategies():
    with open(os.getcwd() + "/source/strategies.json", "r") as file:
        strategies = json.load(file)
        for name, details in strategies.items():
            Strategy.objects.get_or_create(name=name, **details)


def load_all_data():
    # 03@C78B5 40==K5 87 D09;0 crypto_pairs.json
    with open(os.getcwd() + "/source/crypto_pairs.json", "r") as file:
        data = json.load(file)
        for item in data:
            CryptoTradingPair.objects.get_or_create(**item["fields"])

    # =0;>38G=> 4;O stock_pairs.json
    with open(os.getcwd() + "/source/stock_pairs.json", "r") as file:
        data = json.load(file)
        for item in data:
            StockTradingPair.objects.get_or_create(**item["fields"])

    #  4;O strategies.json


def save_manual_settings(request, chosen_strategy, custom_settings):
    # custom_settings = {
    #     k: v
    #     for k, v in request.POST.items()
    #     if k != "csrfmiddlewaretoken"
    #        and k != "chosen_strategy"
    #        and k != "save_manual_strategy"
    # }

    strategy, created = Strategy.objects.get_or_create(
        user=request.user, name=chosen_strategy
    )

    for key, value in custom_settings.items():
        setattr(strategy, key, value)

    strategy.save()


def is_float(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


# Define API permissions dictionary
permissions = {
    "spot": False,
    "margin": False,
    "futures": False,
}
bybit_permissions = {
    "spot": False,
    "derivatives": False,
}


def get_account_api_permissions_bybit(
        bybit_api_key: str, bybit_secret_key: str, max_retries=3
) -> dict | InvalidRequestError | RequestException:
    """
    Get account API permissions for spot, margin, and futures trading.

    Args:
        bybit_api_key (str): The Bybit API key.
        bybit_secret_key (str): The Bybit Secret key.
        max_retries (int, optional): The maximum number of retries. Defaults to 3.

    Returns:
        dict: A dictionary indicating the permissions for spot, margin, and futures trading.
    """

    session = HTTP(
        testnet=False,
        api_key=bybit_api_key,
        api_secret=bybit_secret_key,
    )

    for retry in range(max_retries):
        try:
            data = session.get_api_key_information()["result"]["permissions"]
            if data["Spot"]:
                bybit_permissions["spot"] = True
            if data["Derivatives"]:
                bybit_permissions["derivatives"] = True
            return bybit_permissions
        except InvalidRequestError as ex:
            raise ex
        except RequestException as e:
            print(
                f"Failed to retrieve Bybit API permissions. Retrying ({retry + 1}/{max_retries})..."
            )
            sleep(1)  # Wait for a second before retrying

    return {}


def get_account_api_permissions(api_key, api_secret, max_retries=3) -> dict:
    """
    Get account API permissions for spot, margin, and futures trading.

    Args:
        api_key (str): The Binance API key.
        api_secret (str): The Binance Secret key.
        max_retries (int, optional): The maximum number of retries. Defaults to 3.

    Returns:
        dict: A dictionary indicating the permissions for spot, margin, and futures trading.
    """

    for retry in range(max_retries):
        try:
            client = Client(api_key, api_secret)
            account_info = client.get_account_api_permissions()

            permissions["spot"] = account_info.get("enableSpotAndMarginTrading", False)
            permissions["margin"] = account_info.get("enableMargin", False)
            permissions["futures"] = account_info.get("enableFutures", False)

            return permissions
        except RequestException as e:
            print(
                f"Failed to retrieve Binance API permissions. Retrying ({retry + 1}/{max_retries})..."
            )
            sleep(1)  # Wait for a second before retrying

    return {}


class AESCipher:
    def __init__(self, key: Union[str, bytes]) -> None:
        self.__key = key

    @staticmethod
    def _resolve_key(
            key: Union[str, bytes, bytearray, memoryview]
    ) -> Union[bytes, bytearray, memoryview]:
        try:
            decrypted = list(base64.b64decode(key).decode())
        except binascii.Error:
            return key.encode() if isinstance(key, str) else key
        return base64.b64decode("".join(reversed(decrypted)))

    def encrypt(self, plain_text: str) -> str:
        cipher = AES.new(self._resolve_key(self.__key), AES.MODE_CFB)
        result = list(
            base64.b64encode(cipher.iv + cipher.encrypt(plain_text.encode())).decode()  # type: ignore
        )
        return "".join(reversed(result))

    def decrypt(self, hashed_text: str) -> str:
        data = list(hashed_text)
        decrypted = base64.b64decode("".join(reversed(data)))
        cipher = AES.new(self._resolve_key(self.__key), AES.MODE_CFB, iv=decrypted[:16])  # type: ignore
        return cipher.decrypt(decrypted[16:]).decode()  # type: ignore


async def get_right_minimal_investment_bybit(symbol):
    session = HTTP(testnet=False)
    response = session.get_instruments_info(
        category="linear",
        symbol=symbol.upper(),
    )
    if response["retCode"] == 0:
        min_leverage = response["result"]["list"][0]["leverageFilter"]["minLeverage"]
        max_leverage = response["result"]["list"][0]["leverageFilter"]["maxLeverage"]
        # min_order_quantity = response["result"]["list"][0]["lotSizeFilter"][
        #     "minOrderQty"
        # ]
        # max_order_quantity = response["result"]["list"][0]["lotSizeFilter"][
        #     "maxOrderQty"
        # ]
        min_order_quantity = float(response["result"]["list"][0]["lotSizeFilter"]["minOrderQty"])
        min_notional_quantity = float(response["result"]["list"][0]["lotSizeFilter"]["minNotionalValue"])
        max_order_quantity = float(response["result"]["list"][0]["lotSizeFilter"]["maxOrderQty"])
        current_symbol_price = await get_current_price(symbol)
        min_total_usdt = round(min_order_quantity * current_symbol_price, 2)
        max_total_usdt = round(max_order_quantity * current_symbol_price, 2)
        if min_total_usdt < min_notional_quantity:
            min_total_usdt = min_notional_quantity
        print(min_leverage, max_leverage)

        return {
            "min_leverage": min_leverage,
            "max_leverage": round(float(max_leverage)),
            "min_total": min_total_usdt,
            "max_total": max_total_usdt,
        }
    else:
        raise "Error while getting minimal investment data for Bybit"


async def get_right_minimal_investment_for_each_symbol(symbol):
    url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    response = requests.get(url)
    notional = 0
    min_qty = 0
    info = 0
    if response.status_code == 200:
        exchange_info = response.json()
        symbols = exchange_info.get("symbols", [])

        for symbol_info in symbols:
            if symbol_info.get("symbol") == symbol:
                filters = symbol_info.get("filters", [])
                notional = float(
                    next((f["notional"] for f in filters if f.get("notional")), 0)
                )
                min_qty = float(
                    next((f["minQty"] for f in filters if f.get("minQty")), 0)
                )
                break

        if notional == 0 or min_qty == 0:
            raise ValueError(
                f"Error while trying to get notional or min_qty for symbol {symbol}"
            )

        print(f"{notional=}")
        print(f"{min_qty=}")

        value_to_round = 0 if min_qty >= 1 else int(-1 * round(math.log10(min_qty)))
        print(f"{value_to_round=}")

        asset_price = await get_current_price(symbol)

        number = notional / asset_price
        rounded_number = round(number + 0.5 * 10 ** (-value_to_round), value_to_round)

        for info in exchange_info["symbols"]:
            if info["symbol"] == symbol:
                info = info

        return rounded_number, info, asset_price

    else:
        # Printing an error message if the request was not successful
        print(f"Error: {response.status_code}, {response.text}")
        return 0


async def get_current_price(symbol) -> float:
    url = "https://fapi.binance.com"

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(
                    url + f"/fapi/v1/ticker/price?symbol={symbol}"
            ) as response:
                response.raise_for_status()
                data = await response.json()

        current_price = float(data["price"])
        return current_price
    except Exception as e:
        return 0


def get_symbol_info(symbol):
    base_url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
    response = requests.get(base_url)

    if response.status_code == 200:
        exchange_info = response.json()
        for info in exchange_info["symbols"]:
            if info["symbol"] == symbol:
                return info
    else:
        print(f"Error: {response.status_code}, {response.text}")
        return None


def calculate_min_quantity(symbol_info):
    filters = symbol_info["filters"]

    # 0E>48< D8;LB@ ?> LOT_SIZE
    lot_size_filter = next(
        filter(lambda f: f["filterType"] == "LOT_SIZE", filters), None
    )

    if lot_size_filter:
        min_qty = float(lot_size_filter["minQty"])
        return min_qty
    else:
        return None


def get_binance_client(api, secret):
    return Client(api, secret)


async def get_max_leverage(symbol, api, secret):
    url = "/fapi/v1/leverageBracket"
    params = {"symbol": symbol}
    response = send_signed_default_request("GET", url, api, secret, params)[0]
    brackets = response["brackets"][0]
    max_leverage = brackets["initialLeverage"]
    return int(max_leverage)


def timing_decorator(func):
    def wrapper(*args, **kwargs):
        start_time = time.time()
        result = func(*args, **kwargs)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"@5<O 2K?>;=5=8O DC=:F88 {func.__name__}: {elapsed_time} A5:C=4.")
        return result

    return wrapper


def get_open_orders_and_positions_bybit(symbol, api_key, api_secret, type):
    result = None
    if type == 'orders':
        response = send_signed_bybit_default_request(
            "GET", "/v5/order/realtime", api_key, api_secret, payload=f'symbol={symbol}&category=linear'
        )

        if "result" in response:
            result = response['result']['list']
            result = len(result)
            print(result)
    else:
        response = send_signed_bybit_default_request(
            "GET", "/v5/position/list", api_key, api_secret, payload=f'symbol={symbol}&category=linear'
        )

        if "result" in response:
            result = response['result']['list']
            result = float(result[0]["size"])
            print(result)

    return result


def get_available_balance_bybit(api_key, api_secret):
    balance = 0
    response = send_signed_bybit_default_request(
        "GET", "/contract/v3/private/account/wallet/balance", api_key, api_secret, payload='coin=USDT'
    )

    if "result" in response and "list" in response["result"]:
        for item in response["result"]["list"]:
            if item["coin"] == "USDT":
                balance = item["availableBalance"]
                return float(balance)

    if balance < 1:
        response = send_signed_bybit_default_request(
            "GET", "/v5/account/wallet-balance", api_key, api_secret, payload='accountType=UNIFIED&settleCoin=USDT'
        )

        if "result" in response:
            coin_list = response["result"]["list"]
            for account_data in coin_list:
                coins = account_data.get("coin", [])
                for coin_data in coins:
                    if coin_data.get("coin") == "USDT":
                        balance = float(coin_data.get("availableToWithdraw", 0))
                        return float(balance)
    return 0.0


def get_available_balance_binance_futures(api_key, api_secret):
    response = send_signed_default_request(
        "GET", "/fapi/v2/balance", api_key, api_secret
    )
    for item in response:
        if item["asset"] == "USDT":
            balance = item["availableBalance"]
            return float(balance)
        else:
            pass


def optimize_for_create_ats(user, request, data: dict, activity, just_backtest):
    if request.method == "GET":
        chosen_strategy = data["chosen_strategy"]
        chosen_exchange = data["chosen_exchange"]
        chosen_asset = data["chosen_asset"]
        total_investment = data["total_investment"]
        days_of_backtest = 30

        custom_user = get_object_or_404(CustomUser, id=user.id)

        if chosen_strategy == "f1":
            if activity == "backtest":
                with open(os.getcwd() + "/source/strategies.json", "r") as file:
                    data = json.load(file)
                    interval_for_backtest = data["f1"]["interval"]
            else:
                interval_for_backtest = 0
            # url =  os.getenv("F1_BACKTEST_AND_OPTIMIZER_API_BACKTEST_URL_TEST")
            url = os.getenv("F1_BACKTEST_AND_OPTIMIZER_API_BACKTEST_URL_PROD")
            data = {
                "chosen_strategy": chosen_strategy,
                "symbol": chosen_asset,
                "days_of_backtest": days_of_backtest,
                "just_backtest": just_backtest,
                "interval_for_backtest": interval_for_backtest,
                "start_balance": total_investment,
            }
            response = requests.post(url, data=data)
            if response.status_code == 200:
                result = response.json()
                optimized_settings = {"interval": result["interval"]}
                instance = OptimizedStrategies(
                    json_data=result,
                    user=custom_user,
                    optimized_settings=optimized_settings,
                    strategy=chosen_strategy
                )

                instance.save()

                data = {
                    "Symbol": result["symbol"],
                    "Start balance": "$" + str(result["start balance"]),
                    "TP trades": str(result["TP"])
                                 + " "
                                 + f"(+${str(result['TP in $'])})",
                    "SL trades": str(result["SL"])
                                 + " "
                                 + f"(-${str(result['SL in $'])})",
                    "Trend": str(result["current trend"]),
                    "Margin": "$" + str(result["margin in $"]),
                    "Fees total": "$"
                                  + str(result["fees"])
                                  + " "
                                  + f"({str(result['total trades'])} trades)",
                    "PNL": "$"
                           + str(result["PNL in $"])
                           + " "
                           + f"({str(result['PNL in %'])}%)",
                    "Drawdown": "in progress...",
                    "End balance": "$" + str(result["end balance"]),
                }
                current_date = datetime.datetime.now()
                backtest_and_optimization_history = BacktestAndOptimizationHistory()
                backtest_and_optimization_history.user_id = request.user.id
                backtest_and_optimization_history.asset = data["Symbol"]
                backtest_and_optimization_history.strategy = chosen_strategy
                backtest_and_optimization_history.activity = activity
                backtest_and_optimization_history.date_from = (
                        current_date - datetime.timedelta(days=30)
                ).strftime("%Y-%m-%d")
                backtest_and_optimization_history.date_to = current_date.strftime(
                    "%Y-%m-%d"
                )
                backtest_and_optimization_history.pnl = float(result["PNL in $"])
                backtest_and_optimization_history.data = data
                backtest_and_optimization_history.save()
                # request.session["optimize_create_ats_results"] = data
                return [str(result["PNL in %"]), True]
                # TODO results of optimization save to request session
                # return data
            else:
                print(
                    f"H81:0 ?@8 2K?>;=5=88 POST-70?@>A0. >4 A>AB>O=8O: {response.status_code}"
                )


def backtest_and_optimize_request(user, request, activity, just_backtest):
    if request.method == "GET":
        chosen_strategy = request.GET.get("chosen_strategy").lower()
        chosen_asset = request.GET.get("chosen_asset").upper()
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")
        # interval_for_backtest = request.GET.get('interval_for_backtest')
        total_investment = int(request.GET.get("total_investment", 1000))
        leverage = request.GET.get("leverage")
        margin_type = request.GET.get("margin_type")
        timeframe = request.GET.get("timeframe")

        days_of_backtest = 30
        if chosen_strategy == "f1":
            if activity == "backtest":
                with open(os.getcwd() + "/source/strategies.json", "r") as file:
                    data = json.load(file)
                    interval_for_backtest = data["f1"]["interval"]
            else:
                interval_for_backtest = 0
            # url = os.getenv("F1_BACKTEST_AND_OPTIMIZER_API_BACKTEST_URL_TEST")
            url = os.getenv("F1_BACKTEST_AND_OPTIMIZER_API_BACKTEST_URL_PROD")
            data = {
                "chosen_strategy": chosen_strategy,
                "symbol": chosen_asset,
                "days_of_backtest": days_of_backtest,
                "just_backtest": just_backtest,
                "interval_for_backtest": interval_for_backtest,
                "start_balance": total_investment,
            }
            response = requests.post(url, data=data)
            if response.status_code == 200:
                result = response.json()
                data = {
                    "Symbol": result["symbol"],
                    "Start balance": "$" + str(result["start balance"]),
                    "TP trades": str(result["TP"])
                                 + " "
                                 + f"(+${str(result['TP in $'])})",
                    "SL trades": str(result["SL"])
                                 + " "
                                 + f"(-${str(result['SL in $'])})",
                    "Trend": str(result["current trend"]),
                    "Margin": "$" + str(result["margin in $"]),
                    "Fees total": "$"
                                  + str(result["fees"])
                                  + " "
                                  + f"({str(result['total trades'])} trades)",
                    "PNL": "$"
                           + str(result["PNL in $"])
                           + " "
                           + f"({str(result['PNL in %'])}%)",
                    "Drawdown": "in progress...",
                    "End balance": "$" + str(result["end balance"]),
                }
                if activity == "optimize":
                    request.session["optimize_results"] = response.json()
                backtest_and_optimization_history = BacktestAndOptimizationHistory()
                backtest_and_optimization_history.user_id = request.user.id
                backtest_and_optimization_history.asset = data["Symbol"]
                backtest_and_optimization_history.strategy = chosen_strategy
                backtest_and_optimization_history.activity = activity
                backtest_and_optimization_history.date_from = date_from
                backtest_and_optimization_history.date_to = date_to
                backtest_and_optimization_history.pnl = float(result["PNL in $"])
                backtest_and_optimization_history.data = data
                backtest_and_optimization_history.save()

                return data
                # return True
            else:
                print(
                    f"H81:0 ?@8 2K?>;=5=88 POST-70?@>A0. >4 A>AB>O=8O: {response.status_code}"
                )
                # return False


def get_curent_user_api_credentials(request):
    salt = base64.b64decode(os.getenv("KEY_SALT"))
    aes = AESCipher(salt)
    binance_api_credentials = BinanceApiCredentials.objects.filter(
        user_id=request.user.id
    )
    this_api_key = aes.decrypt(binance_api_credentials[0].hashed_api_key)
    secret_key = aes.decrypt(binance_api_credentials[0].hashed_secret_key)
    return this_api_key, secret_key


def get_jumper_settings():
    return {
        "timeframe": {
            "name": "timeframe",
            "name_display": "Timeframe",
            "timeframe": "1s",
            "timeframe_list": ["1s", "1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"],
        },
        "order_expiration_by_price_percent_limit": {
            "name": "order_expiration_by_price_percent_limit",
            "name_display": "Price change limit %",
            "order_expiration_by_price_percent_limit": 5,
            "order_expiration_by_price_percent_limit_start": 5,
            "order_expiration_by_price_percent_limit_end": 5,
            "order_expiration_by_price_percent_limit_step": 5,
        },
        "long_entry_sum_in_dollars": {
            "name": "long_entry_sum_in_dollars",
            "name_display": "Amount for long",
            "long_entry_sum_in_dollars": 10,
            "long_entry_sum_in_dollars_start": 10,
            "long_entry_sum_in_dollars_end": 30,
            "long_entry_sum_in_dollars_step": 10,
        },
        "short_entry_sum_in_dollars": {
            "name": "short_entry_sum_in_dollars",
            "name_display": "Amount for short",
            "short_entry_sum_in_dollars": 10,
            "short_entry_sum_in_dollars_start": 10,
            "short_entry_sum_in_dollars_end": 30,
            "short_entry_sum_in_dollars_step": 10,
        },
        "long_period": {
            "name": "long_period",
            "name_display": "Long Period",
            "long_period": 5,
            "long_period_start": 5,
            "long_period_end": 5,
            "long_period_step": 5,
        },
        "short_period": {
            "name": "short_period",
            "name_display": "Short Period",
            "short_period": 5,
            "short_period_start": 5,
            "short_period_end": 5,
            "short_period_step": 5,
        },
        "price_difference_long_entry": {
            "name": "price_difference_long_entry",
            "name_display": "Long Divergence %",
            "price_difference_long_entry": 0.1,
            "price_difference_long_entry_start": 0.1,
            "price_difference_long_entry_end": 0.1,
            "price_difference_long_entry_step": 0.1,
        },
        "price_difference_short_entry": {
            "name": "price_difference_short_entry",
            "name_display": "Short Divergence %",
            "price_difference_short_entry": 0.1,
            "price_difference_short_entry_start": 0.1,
            "price_difference_short_entry_end": 0.1,
            "price_difference_short_entry_step": 0.1,
        },
        "long_take_profit_percent": {
            "name": "long_take_profit_percent",
            "name_display": "Long TP %",
            "long_take_profit_percent": 50,
            "long_take_profit_percent_start": 50,
            "long_take_profit_percent_end": 50,
            "long_take_profit_percent_step": 50,
        },
        "short_take_profit_percent": {
            "name": "short_take_profit_percent",
            "name_display": "Short TP %",
            "short_take_profit_percent": 50,
            "short_take_profit_percent_start": 50,
            "short_take_profit_percent_end": 50,
            "short_take_profit_percent_step": 50,
        },
        "long_stop_loss_percent": {
            "name": "long_stop_loss_percent",
            "name_display": "Long SL %",
            "long_stop_loss_percent": 5,
            "long_stop_loss_percent_start": 5,
            "long_stop_loss_percent_end": 5,
            "long_stop_loss_percent_step": 5,
        },
        "short_stop_loss_percent": {
            "name": "short_stop_loss_percent",
            "name_display": "Short SL %",
            "short_stop_loss_percent": 5,
            "short_stop_loss_percent_start": 5,
            "short_stop_loss_percent_end": 5,
            "short_stop_loss_percent_step": 5,
        },
        "long_trailing_stop": {
            "name": "long_trailing_stop",
            "name_display": "Long trailing stop",
            "long_trailing_stop": 0.1,
            "long_trailing_stop_start": 0.1,
            "long_trailing_stop_end": 0.1,
            "long_trailing_stop_step": 0.1,
        },
        "short_trailing_stop": {
            "name": "short_trailing_stop",
            "name_display": "Short trailing stop",
            "short_trailing_stop": 0.1,
            "short_trailing_stop_start": 0.1,
            "short_trailing_stop_end": 0.1,
            "short_trailing_stop_step": 0.1,
        },
        "long_pause_after_trade_min": {
            "name": "long_pause_after_trade_min",
            "name_display": "Long pause minute",
            "long_pause_after_trade_min": 1,
            "long_pause_after_trade_min_start": 1,
            "long_pause_after_trade_min_end": 1,
            "long_pause_after_trade_min_step": 1,
        },
        "short_pause_after_trade_min": {
            "name": "short_pause_after_trade_min",
            "name_display": "Short pause minute",
            "short_pause_after_trade_min": 1,
            "short_pause_after_trade_min_start": 1,
            "short_pause_after_trade_min_end": 1,
            "short_pause_after_trade_min_step": 1,
        }
    }


def get_bybit_settings():
    return {
        "timeframe_object": {
            "name": "timeframe",
            "name_display": "Timeframe",
            "timeframe": "1m",
            "timeframe_list": ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"],
        },
        "price_range_object": {
            "name": "price_range",
            "name_display": "Price Range",
            "price_range": 12,
            "price_range_start": 12,
            "price_range_end": 72,
            "price_range_step": 10,
        },
        "grids_object": {
            "name": "num_of_grids",
            "name_display": "Grids",
            "num_of_grids": 10,
            "num_of_grids_start": 10,
            "num_of_grids_end": 100,
            "num_of_grids_step": 10,
        },

        "activation_trigger_in_percent_object": {
            "name": "activation_trigger_in_percent",
            "name_display": "Trigger +-%",
            "activation_trigger_in_percent": 1.0,
            "activation_trigger_in_percent_start": 1.0,
            "activation_trigger_in_percent_end": 5.0,
            "activation_trigger_in_percent_step": 0.5,
        },
        "distribution_of_grid_lines_object": {
            "name": "distribution_of_grid_lines",
            "name_display": "Grid Distribution",
            "distribution_of_grid_lines": "LINEAR",
            "distribution_of_grid_lines_list": ["LINEAR", "FIBONACCI"],
        },
        "long_stop_loss_in_percent_object": {
            "name": "long_stop_loss_in_percent",
            "name_display": "Long SL%",
            "long_stop_loss_in_percent": 1.0,
            "long_stop_loss_in_percent_start": 1.0,
            "long_stop_loss_in_percent_end": 5.0,
            "long_stop_loss_in_percent_step": 0.5,
        },
        "short_stop_loss_in_percent_object": {
            "name": "short_stop_loss_in_percent",
            "name_display": "Short SL%",
            "short_stop_loss_in_percent": 1.0,
            "short_stop_loss_in_percent_start": 1.0,
            "short_stop_loss_in_percent_end": 5.0,
            "short_stop_loss_in_percent_step": 0.5,
        },
        "trend_period_object": {
            "name": "trend_period",
            "name_display": "Trend Period",
            "trend_period": 12,
            "trend_period_start": 12,
            "trend_period_end": 72,
            "trend_period_step": 10,
        },
    }


def backtest_and_optimize_request_bybit(request,
                                        activity=None,
                                        chosen_strategy=None,
                                        chosen_exchange=None,
                                        chosen_asset=None):
    try:
        data, url, preset = None, None, None
        if not activity:
            activity_strategy_data = getting_activity_and_strategy_data(request)
            activity = activity_strategy_data["activity"]
            chosen_strategy = activity_strategy_data["chosen_strategy"].lower()
            chosen_exchange = activity_strategy_data["chosen_exchange"].lower()
        user = request.user

        if request.method == "GET":
            if activity == "backtest":
                user_backtest_and_optimization_activity = user.num_of_backtesting
                if chosen_strategy == "expo_grid":
                    url = EXPO_GRID_BACKTEST
                    data = getting_data_from_expo_grid_backtest_request(request)
                elif chosen_strategy == "jumper":
                    url = JUMPER_BACKTEST
                    data = getting_data_from_jumper_backtest_request(request)
                from_ = data["from"]
                to = data["to"]
            elif activity == "optimize":
                user_backtest_and_optimization_activity = user.num_of_optimization
                if chosen_strategy == "expo_grid":
                    url = EXPO_GRID_OPTIMIZATION
                elif chosen_strategy == "jumper":
                    url = JUMPER_OPTIMIZATION
                try:
                    data = json.loads(request.GET["requestData"])
                    preset = json.loads(request.GET["isAdmin"])
                except:
                    result = BacktestAndOptimizationHistory.objects.filter(
                        activity=activity, exchange=chosen_exchange,
                        strategy='preset-' + chosen_strategy, asset=chosen_asset).last()

                    return [result, True]

                symbol = data.get("symbol")
                leverage = data.get("leverage")
                available_balance = data.get("available_balance")
                from_ = data.get("from_date")
                to = data.get("to_date")
                data = {
                    "symbol": symbol,
                    "leverage": leverage,
                    "available_balance": available_balance,
                    "from": from_,
                    "to": to,
                    "data": json.dumps(data),
                }
            else:
                # Handle other activities if necessary
                return None

            #59 Create a record in backtest_and_optimization_history immediately after clicking backtest or optimization
            if preset:
                chosen_strategy = 'preset-' + chosen_strategy

            # 227-BacktestingAndOptimizationUpdating
            if user_backtest_and_optimization_activity == 0:
                return ["Sorry, not enough backtests or optimizations on your account", True]

            user_backtest_and_optimization_activity -= 1
            if activity == "backtest":
                user.num_of_backtesting = user_backtest_and_optimization_activity
            elif activity == "optimize":
                user.num_of_optimization = user_backtest_and_optimization_activity
            # 264-OptimizationsAndBacktestsNotifications
            user_stats = UserStatus.objects.get(user_id=user.id)
            user_services = 1
            if activity == "backtest":
                user_services = user_stats.max_backtests
            elif activity == "optimize":
                user_services = user_stats.max_optimizations

            if ((user_backtest_and_optimization_activity / user_services) * 100) == 10:
                tasks.send_alert_email.delay(user.email, user.username, user_backtest_and_optimization_activity,
                                             activity)
            # 264-OptimizationsAndBacktestsNotifications
            user.save()
            # 227-BacktestingAndOptimizationUpdating

            backtest_and_optimization_id = backtest_and_optimization_history_saver(
                request=request,
                data=data,
                chosen_strategy=chosen_strategy,
                chosen_exchange=chosen_exchange,
                activity=activity,
                from_=from_,
                to=to,
            )
            # 60-DataFromOptimizer
            data['backtest_and_optimization_id'] = backtest_and_optimization_id
            # 60-DataFromOptimizer
            response = requests.post(url, data=data, timeout=1800)
            if response.status_code == 200:
                result = response.json()
                # 233-StartTradingButtonLogicToMobileDashboardArchive
                if activity == 'backtest':
                    if 'expo' in chosen_strategy:
                        settings = {
                            "TIMEFRAME": result["TIMEFRAME"],
                            "PRICE RANGE": result["PRICE RANGE"],
                            "NUM OF GRIDS": result["NUM OF GRIDS"],
                            "TREND PERIOD": result["TREND PERIOD"],
                            "TREND PERIOD TIMEFRAME": result["TREND PERIOD TIMEFRAME"],
                            "GRID DISBALANCE DIRECTION": result["GRID DISBALANCE DIRECTION"],
                            "LINE DISBALANCE DIRECTION": result["LINE DISBALANCE DIRECTION"],
                            "LONG STOP LOSS IN PERCENT": result["LONG STOP LOSS IN PERCENT"],
                            "DISTRIBUTION OF GRID LINES": result["DISTRIBUTION OF GRID LINES"],
                            "SHORT STOP LOSS IN PERCENT": result["SHORT STOP LOSS IN PERCENT"],
                            "ACTIVATION TRIGGER IN PERCENT": result["ACTIVATION TRIGGER IN PERCENT"]
                        }
                        result["SETTINGS"] = settings
                # 233-StartTradingButtonLogicToMobileDashboardArchive
                backtest_and_optimization_history_saver(
                    request=request,
                    data=result,
                    chosen_strategy=chosen_strategy,
                    chosen_exchange=chosen_exchange,
                    activity=activity,
                    from_=from_,
                    to=to,
                    backtest_and_optimization_id=backtest_and_optimization_id
                )

                if activity == "optimize":
                    custom_user = get_object_or_404(CustomUser, id=user.id)
                    optimized_settings = result["SETTINGS"]
                    instance = OptimizedStrategies(
                        json_data=result,
                        user=custom_user,
                        optimized_settings=optimized_settings,
                        strategy=chosen_strategy,
                        exchange=chosen_exchange
                    )
                    instance.save()

                return [result, True]

            # 26-OptimizationAndBacktestParametersErrors
            backtest_and_optimization_history = BacktestAndOptimizationHistory.objects.get(
                id=backtest_and_optimization_id
            )
            backtest_and_optimization_history.asset = data["symbol"]
            backtest_and_optimization_history.status = 'failed'
            backtest_and_optimization_history.progress = -1
            backtest_and_optimization_history.save()

            return [{"error": response.text}, False]
            # 26-OptimizationAndBacktestParametersErrors
    except Exception as e:
        print(e)
        return [e, False]


def backtest_and_optimization_history_saver(request, data, chosen_strategy, chosen_exchange, activity, from_, to,
                                            backtest_and_optimization_id=None):
    print(chosen_strategy, chosen_exchange)


    date_obj_from = datetime.datetime.strptime(from_, "%d-%m-%Y")
    date_from = date_obj_from.strftime("%Y-%m-%d")

    date_obj_to = datetime.datetime.strptime(to, "%d-%m-%Y")
    date_to = date_obj_to.strftime("%Y-%m-%d")

    # 59 Create a record in backtest_and_optimization_history immediately after clicking backtest or optimization
    if backtest_and_optimization_id:
        pnl = 0
        if chosen_strategy == "expo_grid" or chosen_strategy == "preset-expo_grid":
            # pnl = round(100 * data["AVAILABLE BALANCE"] / data["INITIAL BALANCE"] - 100, 1)
            pnl = "{:.2f}".format(100 * data["AVAILABLE BALANCE"] / data["INITIAL BALANCE"] - 100)

        if chosen_strategy == "jumper" or chosen_strategy == "preset-jumper":
            pnl = "{:.2f}".format(100 * data["END BALANCE"] / data["INVESTMENT"] - 100)

        backtest_and_optimization_history = BacktestAndOptimizationHistory.objects.get(
            id=backtest_and_optimization_id
        )
        # Update the existing record with new data
        backtest_and_optimization_history.asset = data["ASSET"]
        backtest_and_optimization_history.pnl = pnl
        backtest_and_optimization_history.data = data
        # 57-iterationsAndStatusesForBacktestAndOptimizationHistory
        backtest_and_optimization_history.status = 'success'
        finish = backtest_and_optimization_history.final_progress_number
        backtest_and_optimization_history.progress = finish
        # 57-iterationsAndStatusesForBacktestAndOptimizationHistory
        backtest_and_optimization_history.save()
    else:
        # Create new record
        backtest_and_optimization_history = BacktestAndOptimizationHistory()
        backtest_and_optimization_history.user_id = request.user.id
        backtest_and_optimization_history.strategy = chosen_strategy
        backtest_and_optimization_history.exchange = chosen_exchange
        backtest_and_optimization_history.activity = activity
        backtest_and_optimization_history.date_from = date_from
        backtest_and_optimization_history.date_to = date_to
        backtest_and_optimization_history.data = 'empty'
        backtest_and_optimization_history.save()

    return backtest_and_optimization_history.id


# 314-DB2Range
def get_assets_list(request=None):
    try:
        all_asset_ranges = cache.get('assets_range')
        if not all_asset_ranges:
            all_asset_ranges = {
                "dexima_XRPUSDT_futures_1m": {
                    "start_date": "2022-01-11 00:00:00",
                    "end_date": "2024-06-10 23:59:59"
                }
            }

        dexima_1m_keys = [k for k in all_asset_ranges.keys() if k.startswith('dexima') and k.endswith('futures_1m')]
        dexima_symbols = [key.split('_')[1] for key in dexima_1m_keys]

        if request:
            return JsonResponse({'dexima_symbols_list': dexima_symbols})
        else:
            return dexima_symbols, all_asset_ranges
    except Exception as e:
        print(f"An error occurred, no assets range: {e}")
        return None
# 314-DB2Range

def get_binance_assets():
    # List of popular cryptocurrency symbols
    popular_symbols = cache.get("popular_symbols")
    if not popular_symbols:
        popular_symbols = [
            "BTCUSDT",
            "ETHUSDT",
            "XRPUSDT",
            "LTCUSDT",
            "TRXUSDT",
            "ETCUSDT",
            "ADAUSDT",
            "VETUSDT",
            "DOGEUSDT",
            "SOLUSDT",
            "DOTUSDT",
            "BATUSDT",
            "RVNUSDT",
            "KAVAUSDT",
            "WAVESUSDT",
            "LINKUSDT",
            "MATICUSDT",
            "AVAXUSDT",
            "ATOMUSDT",
            "XMRUSDT",
            "FILUSDT",
            "NEOUSDT",
            "BCHUSDT",
            "UNIUSDT",
            "XLMUSDT",
            "RUNEUSDT",
            "ICPUSDT",
            "LDOUSDT",
            "HBARUSDT",
            "APTUSDT",
        ]
        cache.set("popular_symbols", popular_symbols, 50000)

    return popular_symbols


def getting_activity_and_strategy_data(request):
    symbol = request.GET.get("symbol")
    chosen_strategy = request.GET.get("strategy")
    chosen_exchange = request.GET.get("chosen_exchange")
    activity = request.GET.get("activity")

    return {
        "symbol": symbol,
        "chosen_strategy": chosen_strategy,
        "chosen_exchange": chosen_exchange,
        "activity": activity,
    }


def getting_data_from_jumper_backtest_request(request):
    symbol = request.GET.get("symbol")
    chosen_strategy = request.GET.get("strategy")
    activity = request.GET.get("activity")
    leverage = request.GET.get("leverage")
    available_balance = request.GET.get("available_balance")
    timeframe = request.GET.get("timeframe")
    from_ = request.GET.get("from")
    to = request.GET.get("to")
    long_entry_sum_in_dollars = request.GET.get("long_entry_sum_in_dollars")
    short_entry_sum_in_dollars = request.GET.get("short_entry_sum_in_dollars")
    long_take_profit_percent = request.GET.get("long_take_profit_percent")
    long_stop_loss_percent = request.GET.get("long_stop_loss_percent")
    short_take_profit_percent = request.GET.get("short_take_profit_percent")
    short_stop_loss_percent = request.GET.get("short_stop_loss_percent")
    price_difference_long_entry = request.GET.get("price_difference_long_entry")
    price_difference_short_entry = request.GET.get("price_difference_short_entry")
    block_long_trade_until = None
    block_short_trade_until = None
    long_pause_after_trade_min = request.GET.get("long_pause_after_trade_min")
    short_pause_after_trade_min = request.GET.get("short_pause_after_trade_min")
    order_expiration_by_price_percent_limit = request.GET.get("order_expiration_by_price_percent_limit")
    short_period = request.GET.get("short_period")
    long_period = request.GET.get("long_period")
    long_trailing_stop = request.GET.get("long_trailing_stop")
    short_trailing_stop = request.GET.get("short_trailing_stop")

    return {
        "symbol": symbol,
        "chosen_strategy": chosen_strategy,
        "activity": activity,
        "leverage": leverage,
        "available_balance": available_balance,
        "timeframe": timeframe,
        "from": from_,
        "to": to,
        "long_entry_sum_in_dollars": long_entry_sum_in_dollars,
        "short_entry_sum_in_dollars": short_entry_sum_in_dollars,
        "long_take_profit_percent": long_take_profit_percent,
        "long_stop_loss_percent": long_stop_loss_percent,
        "short_take_profit_percent": short_take_profit_percent,
        "short_stop_loss_percent": short_stop_loss_percent,
        "price_difference_long_entry": price_difference_long_entry,
        "price_difference_short_entry": price_difference_short_entry,
        "block_long_trade_until": block_long_trade_until,
        "block_short_trade_until": block_short_trade_until,
        "long_pause_after_trade_min": long_pause_after_trade_min,
        "short_pause_after_trade_min": short_pause_after_trade_min,
        "order_expiration_by_price_percent_limit": order_expiration_by_price_percent_limit,
        "short_period": short_period,
        "long_period": long_period,
        "long_trailing_stop": long_trailing_stop,
        "short_trailing_stop": short_trailing_stop,
    }


def getting_data_from_expo_grid_backtest_request(request):
    symbol = request.GET.get("symbol")
    chosen_strategy = request.GET.get("strategy")
    activity = request.GET.get("activity")
    leverage = request.GET.get("leverage")
    num_of_grids = request.GET.get("num_of_grids")
    available_balance = request.GET.get("available_balance")
    timeframe = request.GET.get("timeframe")
    price_range = request.GET.get("price_range")
    activation_trigger_in_percent = request.GET.get("activation_trigger_in_percent")
    distribution_of_grid_lines = request.GET.get("distribution_of_grid_lines")
    line_disbalance_direction = request.GET.get("line_disbalance_direction")
    short_stop_loss_in_percent = request.GET.get("short_stop_loss_in_percent")
    long_stop_loss_in_percent = request.GET.get("long_stop_loss_in_percent")
    grid_disbalance_direction = request.GET.get("grid_disbalance_direction")
    trend_period_timeframe = request.GET.get("trend_period_timeframe")
    trend_period = request.GET.get("trend_period")
    from_ = request.GET.get("from")
    to = request.GET.get("to")

    return {
        "symbol": symbol,
        "chosen_strategy": chosen_strategy,
        "activity": activity,
        "leverage": leverage,
        "num_of_grids": num_of_grids,
        "available_balance": available_balance,
        "timeframe": timeframe,
        "price_range": price_range,
        "activation_trigger_in_percent": activation_trigger_in_percent,
        "distribution_of_grid_lines": distribution_of_grid_lines,
        "line_disbalance_direction": line_disbalance_direction,
        "short_stop_loss_in_percent": short_stop_loss_in_percent,
        "long_stop_loss_in_percent": long_stop_loss_in_percent,
        "grid_disbalance_direction": grid_disbalance_direction,
        "trend_period_timeframe": trend_period_timeframe,
        "trend_period": trend_period,
        "from": from_,
        "to": to,
    }


if __name__ == "__main__":
    print(get_account_api_permissions_bybit())
    # key = os.getenv("KEY_SALT")
    # # salt = os.urandom(32)
    # salt = base64.b64decode(key)
    # aes = AESCipher(salt)
    #
    # plain_text = "Maks"
    # hashed_text = aes.encrypt(plain_text)
    # print(hashed_text)
    # print(aes.decrypt(hashed_text))
    # print(base64.b64encode(salt).decode(encoding='utf-8'))
