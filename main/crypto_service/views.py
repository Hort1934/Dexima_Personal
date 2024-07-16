import base64
import datetime
import os
import aiohttp
import requests

from django.db.models import Sum, Count
from django.utils import timezone
from django.http import JsonResponse
from django.http import HttpResponse
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.shortcuts import render

from main_service.forms import StartBotForm
from source.decorators import set_user_language
from main_service.models import (
    CustomUser,
    BinanceApiCredentials,
    BybitApiCredentials,
    UserStatus
)
from crypto_service.models import OptimizedStrategies, TradingBots, BotsStatistic
from source.utils import (
    backtest_and_optimize_request,
    AESCipher,
    get_open_orders_and_positions_bybit,
    get_available_balance_binance_futures,
    get_available_balance_bybit,
    get_binance_client,
    optimize_for_create_ats,
    get_binance_assets,
    get_assets_list,
    backtest_and_optimize_request_bybit,
)

from config import JUMPER_START_BOT, EXPO_GRID_START_BOT


@user_passes_test(lambda user: user.is_staff, login_url="/")
def admin_dashboard(request):
    stats_start, stats_profit, stats_total, summary_total = 0, 0, 0, 0
    not_closed_position, binance_permissions, duplicate_symbol_started_bot = (
        False,
        False,
        False,
    )
    user_have_enough_money = True
    all_users_bots, all_users_archive_bots = [], []
    user = request.user

    """
        Check if user have permissions for trade on Binance    
    """

    binance_credentials = BinanceApiCredentials.objects.filter(user_id=user.id)
    if binance_credentials:
        try:
            if (
                "FUTURES"
                and "SPOT" in binance_credentials[0].permissions["permissions"]
            ):
                binance_permissions = True
        except Exception as ex:
            print(ex)
    else:
        pass
    """
           Check if user have started bot for same symbol already  
    """
    duplicate_trading_pairs = (
        TradingBots.objects.filter(user_id=user.id)
        .values("trading_pair")
        .annotate(count=Count("trading_pair"))
        .filter(count__gt=1)
    )

    if duplicate_trading_pairs:
        first_duplicate_pair = duplicate_trading_pairs[0]["trading_pair"]
        matching_records = TradingBots.objects.filter(
            user_id=user.id, trading_pair=first_duplicate_pair
        )
        for record in matching_records:
            # Проверка статуса
            if record.status == "started":
                duplicate_symbol_started_bot = True
                break  # Прерываем цикл, так как мы уже нашли совпадение

    """
        View for the user's dashboard.
    """
    if request.method == "POST":
        if "total_investment" in request.POST:
            pass

    trading_bots = TradingBots.objects.all()
    for trading_bot in trading_bots:
        trading_bot.running_time = (timezone.now() - trading_bot.launch_date).days
        trading_bot.save()

        current_bot_stats = (
            BotsStatistic.objects.filter(user_id=user.id, trading_bot=trading_bot.id)
            .order_by("-id")
            .aggregate(total_pnl=Sum("realized_pnl"))
        )
        if trading_bot.status == "started":
            all_users_bots.append(trading_bot)
        else:
            all_users_archive_bots.append(trading_bot)
        stats_start += trading_bot.investment_amount
        if current_bot_stats["total_pnl"] is not None:
            trading_bot.profit = round(float(current_bot_stats["total_pnl"]), 2)
            trading_bot.approximately_price_year = round(
                float(current_bot_stats["total_pnl"]) * 12, 2
            )
            trading_bot.save()
    user = request.user

    bot_stats = (
        BotsStatistic.objects.filter(user_id=user.id)
        .order_by("-id")
        .aggregate(total_pnl=Sum("realized_pnl"))
    )
    if bot_stats["total_pnl"] is not None:
        stats_profit = round(bot_stats["total_pnl"], 2)
        if stats_profit is None:
            stats_profit = 0

        stats_total = round(stats_profit, 2) + round(stats_start, 2)
        if stats_start != 0:
            summary_total = round(
                round(stats_profit, 2) * 100 / round(stats_start, 2), 2
            )
        else:
            summary_total = 0
    start_bot_form = StartBotForm()
    if "user_have_enough_money" in request.session:
        user_have_enough_money = request.session.get("user_have_enough_money")

    try:
        not_closed_position = request.session.get("not_closed_position_or_orders")
    except:
        print("not_closed_position_or_orders = False")
    context = {
        "duplicate_symbol_started_bot": duplicate_symbol_started_bot,
        "user_have_binance_permissions": binance_permissions,
        "chosen_strategy": request.session.get("chosen_strategy"),
        "all_users_archive_bots": all_users_archive_bots,
        "all_users_bots": all_users_bots,
        "count_of_bots": len(all_users_bots),
        "user_have_enough_money": user_have_enough_money,
        "start_bot_form": start_bot_form,
        "stats_start": stats_start,
        "stats_profit": stats_profit,
        "stats_total": stats_total,
        "summary_total": summary_total,
        "not_closed_position_or_orders": not_closed_position,
    }
    request.session["user_have_enough_money"] = True
    request.session["not_closed_position_or_orders"] = False
    return render(request, "admin/admin-dashboard.html", context)


async def get_futures_symbols():
    async with aiohttp.ClientSession() as session:
        url = "https://fapi.binance.com/fapi/v1/exchangeInfo"
        async with session.get(url) as response:
            if response.status == 200:
                data = await response.json()
                return data.get("symbols", [])
            else:
                print(f"Error: {response.status}")
                return []


async def get_futures_price_change(session, symbol):
    url = f"https://fapi.binance.com/fapi/v1/ticker/24hr?symbol={symbol}"
    async with session.get(url) as response:
        if response.status == 200:
            data = await response.json()
            return data
        else:
            print(f"Error: {response.status}")
            return None


@login_required
def free_backtesting_counter(request) -> None:
    """
    Decrement the number of backtesting count for a user.
    """
    user = request.user
    if user.num_of_backtesting > 0:
        user.num_of_backtesting -= 1
        user.save()
    # TODO: Handle the scenario when num_of_backtesting <= 0.


@login_required
def free_optimizations_counter(request) -> None:
    """
    Decrement the number of optimization count for a user.
    """
    user = request.user
    if user.num_of_optimization > 0:
        user.num_of_optimization -= 1
        user.save()
    # TODO: Handle the scenario when num_of_optimization <= 0.


@set_user_language
@login_required
def backtest(request):
    user = request.user
    activity = "backtest"
    just_backtest = True
    backtest_result = backtest_and_optimize_request(
        user, request, activity, just_backtest
    )
    return JsonResponse(backtest_result)


def optimize(request):
    user = request.user
    activity = "optimize"
    just_backtest = False
    optimize_result = backtest_and_optimize_request(
        user, request, activity, just_backtest
    )

    return JsonResponse(optimize_result)


def crypto_optimize(request):
    result = {"optimization_completed": False}
    if request.method == "GET":
        activity = "optimize"
        chosen_strategy = request.GET.get("chosen_strategy").lower()
        chosen_asset = request.GET.get("chosen_asset").upper()
        chosen_exchange = request.GET.get("chosen_exchange").lower()
        pnl_and_bool = backtest_and_optimize_request_bybit(request,
                                                           activity,
                                                           chosen_strategy,
                                                           chosen_exchange,
                                                           chosen_asset)
        print(pnl_and_bool)

        if pnl_and_bool[-1]:

            result["optimization_completed"] = pnl_and_bool[-1]
            result["pnl"] = pnl_and_bool[0].pnl
            result["days"] = (pnl_and_bool[0].date_to - pnl_and_bool[0].date_from).days
            result["usdt"] = pnl_and_bool[0].data["INITIAL BALANCE"]
            result["leverage"] = pnl_and_bool[0].data["LEVERAGE"]

        return JsonResponse(result)


def add_to_dashboard_without_optimize(request):
    print("add_to_dashboard_without_optimize_start")
    user = request.user
    if request.method == "GET":
        chosen_strategy = request.GET.get("chosen_strategy").lower()
        chosen_exchange = request.GET.get("chosen_exchange").lower()
        chosen_asset = request.GET.get("chosen_asset")
        total_investment = float(request.GET.get("total_investment", 1000))
        leverage = int(request.GET.get("leverage", 1))
        margin_type = request.GET.get("margin_type", "ISOLATED")

        if chosen_strategy == "f1":
            custom_user = get_object_or_404(CustomUser, id=user.id)
            print(request.session.get("optimize_results"))
            optimized_settings = {
                "interval": request.session.get("optimize_results")["interval"]
            }
            instance = OptimizedStrategies(
                json_data=request.session.get("optimize_results"),
                user=custom_user,
                optimized_settings=optimized_settings,
                strategy=chosen_strategy
            )

            instance.save()

            """ creating of bot """

            current_time = timezone.now()
            custom_user = get_object_or_404(CustomUser, id=user.id)
            trading_bot = TradingBots()
            trading_bot.user = user
            trading_bot.optimized_strategy = OptimizedStrategies.objects.filter(
                user=custom_user, strategy=chosen_strategy,
                json_data__contains={"ASSET": chosen_asset}, exchange=chosen_exchange).last()
            trading_bot.trading_pair = chosen_asset
            trading_bot.strategy_name = chosen_strategy
            trading_bot.exchange = chosen_exchange
            trading_bot.launch_date = current_time.strftime("%Y-%m-%d %H:%M:%S")
            trading_bot.status = "created"
            trading_bot.investment_amount = total_investment
            trading_bot.leverage = leverage
            trading_bot.margin_type = margin_type
            trading_bot.save()
            trading_bot_instance = (
                TradingBots.objects.filter(user_id=user.id).order_by("-id").first()
            )
            instance = (
                OptimizedStrategies.objects.filter(user_id=user.id, strategy=chosen_strategy, exchange=chosen_exchange)
                .order_by("-id")
                .first()
            )
            instance.strategy_id = trading_bot_instance
            instance.save()

            return redirect("main_service:dashboard")


@set_user_language
@login_required
def backtest_optimization(request) -> HttpResponse:
    if request.method == "GET":
        # 314-DB2Range
        dexima_symbols, symbols_list = get_assets_list()
        context = {
            'dexima_symbols_list': dexima_symbols,
            'symbols_list': symbols_list
        }
        # 314-DB2Range
        return render(
            request, "main_service/backtest_and_ai_optimization.html", context
        )


def check_user_api_keys_bybit(request):
    if request.method == "GET":
        user = request.user
        credentials = BybitApiCredentials.objects.filter(user_id=user.id)
        if credentials:
            result = {"keys_saved": True}
        else:
            result = {"keys_saved": False}
        return JsonResponse(result)
    return JsonResponse({"keys_saved": False})


def check_user_api_keys(request):
    if request.method == "GET":
        user = request.user
        credentials = BinanceApiCredentials.objects.filter(user_id=user.id)
        if credentials:
            result = {"keys_saved": True}
        else:
            result = {"keys_saved": False}
        return JsonResponse(result)
    return JsonResponse({"keys_saved": False})


def check_balance(request, total_investment=None):
    available_balance = 0
    if request.method == "GET":

        chosen_exchange = request.GET.get("chosen_exchange").lower()
        if not total_investment:
            total_investment = float(request.GET.get("total_investment"))
        salt = base64.b64decode(os.getenv("KEY_SALT"))
        aes = AESCipher(salt)

        if chosen_exchange == 'binance':
            binance_api_credentials = BinanceApiCredentials.objects.filter(
                user_id=request.user.id
            )

            api_key = aes.decrypt(binance_api_credentials[0].hashed_api_key)
            secret_key = aes.decrypt(binance_api_credentials[0].hashed_secret_key)
            available_balance = float(
                get_available_balance_binance_futures(api_key, secret_key)
            )

        elif chosen_exchange == 'bybit':
            bybit_api_credentials = BybitApiCredentials.objects.filter(
                user_id=request.user.id
            )

            api_key = aes.decrypt(bybit_api_credentials[0].hashed_api_key)
            secret_key = aes.decrypt(bybit_api_credentials[0].hashed_secret_key)
            available_balance = float(
                get_available_balance_bybit(api_key, secret_key)
            )
        print(available_balance)

        if available_balance > total_investment:
            return JsonResponse({"enough_balance": True})
        else:
            return JsonResponse({"enough_balance": False})


def check_pos_and_orders(request):
    if request.method == "GET":

        chosen_exchange = request.GET.get("chosen_exchange").lower()
        symbol = request.GET.get("chosen_asset")
        result_dict = {"no_positions": False, "no_orders": False}
        salt = base64.b64decode(os.getenv("KEY_SALT"))
        aes = AESCipher(salt)
        if chosen_exchange == 'binance':
            binance_api_credentials = BinanceApiCredentials.objects.filter(
                user_id=request.user.id
            )
            api_key = aes.decrypt(binance_api_credentials[0].hashed_api_key)
            secret_key = aes.decrypt(binance_api_credentials[0].hashed_secret_key)

            client = get_binance_client(api_key, secret_key)
            """get position for each symbol"""
            positions = client.futures_position_information()
            position_amt = float(
                [
                    position["positionAmt"]
                    for position in positions
                    if position["symbol"] == symbol
                ][0]
            )
            if position_amt == 0:
                result_dict["no_positions"] = True
            """get open orders for each symbol FALSE if orders not exist, TRUE if orders exist"""
            open_orders = client.futures_get_open_orders(symbol=symbol)
            if not open_orders:
                result_dict["no_orders"] = True
        elif chosen_exchange == 'bybit':
            bybit_api_credentials = BybitApiCredentials.objects.filter(
                user_id=request.user.id
            )

            api_key = aes.decrypt(bybit_api_credentials[0].hashed_api_key)
            secret_key = aes.decrypt(bybit_api_credentials[0].hashed_secret_key)

            open_orders = get_open_orders_and_positions_bybit(symbol, api_key, secret_key, type='orders')
            positions = get_open_orders_and_positions_bybit(symbol, api_key, secret_key, type='positions')

            if positions == 0:
                result_dict["no_positions"] = True

            if open_orders == 0:
                result_dict["no_orders"] = True
        return JsonResponse(result_dict)


# {"no_positions": False, "no_orders": False} if both True create bot


def check_bots(request):
    if request.method == "GET":
        symbol = request.GET.get("chosen_asset")
        exchange = request.GET.get("chosen_exchange").lower()
        active_bot = TradingBots.objects.filter(
            user_id=request.user.id, exchange=exchange, trading_pair=symbol, status='started'
        )

        if active_bot:
            return JsonResponse({"no_bots": False})
        else:
            return JsonResponse({"no_bots": True})


# 230-AccountStatusChecking
def check_account_status(request):
    try:
        if request.method == "GET":
            user = request.user
            user_stats = UserStatus.objects.get(user_id=user.id)
            user_expired_date = user_stats.expiration_date

            time_left = (
                    user_expired_date - datetime.datetime.now(datetime.timezone.utc)
            ).days

            if time_left < 0:
                if user.num_of_backtesting != 0:
                    user.num_of_backtesting = 0
                if user.num_of_optimization != 0:
                    user.num_of_optimization = 0
                if user.num_of_ats != 0:
                    user.num_of_ats = 0
                user.save()
                return JsonResponse({"expired": False})
            else:
                return JsonResponse({"expired": True})
    except UserStatus.DoesNotExist:
        return JsonResponse({"error": "User status does not exist"}, status=404)


# 228-ATSChecking
def check_ats(request):
    if request.method == "GET":
        num_of_ats = request.user.num_of_ats
        active_ats = TradingBots.objects.filter(user_id=request.user.id, status='started')
        if num_of_ats - len(active_ats) > 0:
            return JsonResponse({"no_ats": True})
        else:
            return JsonResponse({"no_ats": False})


def create_bot(request):
    user = request.user
    custom_user = get_object_or_404(CustomUser, id=user.id)
    if request.method == "GET":
        marker = request.GET.get("marker")
        chosen_strategy = request.GET.get("chosen_strategy").lower()
        chosen_exchange = request.GET.get("chosen_exchange").lower()
        chosen_asset = request.GET.get("chosen_asset")
        total_investment = float(request.GET.get("total_investment", 1000))
        leverage = int(request.GET.get("leverage", 1))
        margin_type = request.GET.get("margin_type", "ISOLATED")
        current_time = timezone.now()
        trading_bot = TradingBots()
        trading_bot.user = user
        if marker == 'quick_start':
            chosen_strategy = 'preset-' + chosen_strategy
            #  To create super admin preset logic and to update start_bot for jumper
            trading_bot.optimized_strategy = OptimizedStrategies.objects.filter(
                strategy=chosen_strategy, json_data__contains={"ASSET": chosen_asset}, exchange=chosen_exchange).last()
        else:
            trading_bot.optimized_strategy = OptimizedStrategies.objects.filter(
                user=custom_user, strategy=chosen_strategy,
                json_data__contains={"ASSET": chosen_asset}, exchange=chosen_exchange).last()
        trading_bot.trading_pair = chosen_asset
        trading_bot.strategy_name = chosen_strategy
        trading_bot.exchange = chosen_exchange
        trading_bot.launch_date = current_time.strftime("%Y-%m-%d %H:%M:%S")
        trading_bot.status = "created"
        trading_bot.investment_amount = total_investment
        trading_bot.leverage = leverage
        trading_bot.margin_type = margin_type
        trading_bot.save()
        trading_bot_instance = (
            TradingBots.objects.filter(user_id=user.id).order_by("-id").first()
        )
        return JsonResponse({"strategy_id": trading_bot_instance.id})


def start_bot(request, strategy_id):
    if request.method == "GET":
        # Получаем настройки из оптимизированной стратегии

        trading_bot = TradingBots.objects.get(id=strategy_id)

        # Получаем объект OptimizedStrategies, связанный с TradingBots
        optimized_strategy = trading_bot.optimized_strategy

        # Получаем поле optimized_settings из OptimizedStrategies
        optimized_settings = optimized_strategy.optimized_settings
        print(strategy_id, optimized_strategy, optimized_settings)


        bot_id = TradingBots.objects.filter(id=strategy_id)
        chosen_strategy = trading_bot.strategy_name
        # To create Jumper
        available_balance = optimized_strategy.json_data["AVAILABLE BALANCE"]
        num_of_grids = optimized_settings['NUM OF GRIDS'],
        timeframe = optimized_settings['TIMEFRAME'],
        price_range = optimized_settings['PRICE RANGE'],
        activation_trigger_in_percent = optimized_settings['ACTIVATION TRIGGER IN PERCENT'],
        distribution_of_grid_lines = optimized_settings['DISTRIBUTION OF GRID LINES'],
        line_disbalance_direction = optimized_settings['LINE DISBALANCE DIRECTION'],
        short_stop_loss_in_percent = optimized_settings['SHORT STOP LOSS IN PERCENT'],
        long_stop_loss_in_percent = optimized_settings['LONG STOP LOSS IN PERCENT'],
        long_stop_loss_in_percent = long_stop_loss_in_percent[0]
        grid_disbalance_direction = optimized_settings['GRID DISBALANCE DIRECTION'],
        trend_period_timeframe = optimized_settings['TREND PERIOD TIMEFRAME'],
        trend_period = optimized_settings['TREND PERIOD']

        symbol = trading_bot.trading_pair
        total_investment = float(trading_bot.investment_amount)
        leverage = trading_bot.leverage
        margin_type = trading_bot.margin_type

        # start bot by sending post request to dexima ats

        if chosen_strategy == 'expo_grid' or chosen_strategy == 'preset-expo_grid':
            url = EXPO_GRID_START_BOT
        elif chosen_strategy == 'jumper' or chosen_strategy == 'preset-jumper':
            url = JUMPER_START_BOT
        else:
            url = "http://195.201.70.92:85/api/dexima_ats_f1_bot/start_bot/"
            # url = 'http://127.0.0.1:8025/api/dexima_ats_f1_bot/start_bot/'
        data = {
            "bot_id": bot_id[0].id,
            "user_id": request.user.id,
            "symbol": symbol,
            # "interval": optimized_settings["interval"], ???
            "interval": 0,
            "total_investment": total_investment,
            "leverage": leverage,
            "margin_type": margin_type,
            "available_balance": available_balance,
            "num_of_grids": num_of_grids,
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
        }

        requests.post(url, data=data)
        print("Task added to the queue.")
        instance = TradingBots.objects.get(id=strategy_id)
        instance.status = "started"
        instance.save()
        return JsonResponse({"bot_started": True})
