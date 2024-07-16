import base64
import json
import math
import os
import secrets
import asyncio
import time
import hashlib
import django
import pytz
import requests
import datetime

from binance import Client
from django.db import connections
from django.db.models import Sum, Q
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.contrib.auth import login, get_user_model
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from pybit.unified_trading import HTTP
from django.core.mail import send_mail
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode
from django.http import HttpResponseBadRequest

from source import auto_setting_of_trial_status
from crypto_service.models import TradingBots, OptimizedStrategies, BotsStatistic

from . import tasks
from .forms import NewUserForm, SupportForm
from main_service.models import (
    CustomUser,
    BinanceApiCredentials,
    BybitApiCredentials,
    BacktestAndOptimizationHistory,
    Statuses,
    UserStatus,
)
from config import (
    BACKTEST_COST,
    OPTIMIZATION_COST,
    api_secret,
    api_key,
    EXPO_GRID_BACKTEST,
    EXPO_GRID_OPTIMIZATION,
    EXPO_GRID_START_BOT,
    EXPO_GRID_STOP_BOT,
    JUMPER_BACKTEST,
    JUMPER_OPTIMIZATION,
    JUMPER_START_BOT,
    JUMPER_STOP_BOT,
)
from source.decorators import set_user_language

# from source.email_verifier import email_sender
from source.utils import (
    get_account_api_permissions,
    AESCipher,
    get_right_minimal_investment_for_each_symbol,
    get_current_price,
    calculate_min_quantity,
    get_binance_client,
    get_max_leverage,
    timing_decorator,
    get_available_balance_binance_futures,
    get_curent_user_api_credentials,
    get_account_api_permissions_bybit,
    get_bybit_settings,
    get_right_minimal_investment_bybit,
    backtest_and_optimize_request_bybit,
    get_jumper_settings,
    backtest_and_optimization_history_saver,
)

from crypto_service.views import (check_user_api_keys_bybit, check_user_api_keys, check_bots, check_pos_and_orders,
                                  check_balance, check_ats, check_account_status)


os.environ.setdefault("DJANGO_SETTINGS_MODULE", "dexima_ats_web_service.settings")
django.setup()

from django.http import JsonResponse
from django.core import serializers
from django.views.generic import View
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import PasswordResetForm
from source.email_verifier import forgot_password_sender
from django.core.cache import cache

#
class CustomPasswordResetView(View):
    def post(self, request, *args, **kwargs):
        print("custom form")
        form = PasswordResetForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data.get('email')
            try:
                forgot_password_sender(email)
                return render(request, "registration/password_reset_done.html")
            except Exception as e:
                return JsonResponse({'success': False, 'error': str(e)}, status=500)
        else:
            return JsonResponse({'success': False, 'error': 'Invalid form data'}, status=400)


@set_user_language
@login_required
def api_keys_update(request):
    if request.method == "GET":
        user = request.user
        user_api_keys = {}
        if BinanceApiCredentials.objects.filter(user_id=user.id):
            user_api_keys["binance"] = True
        if BybitApiCredentials.objects.filter(user_id=user.id):
            user_api_keys["bybit"] = True
        context = {"user_api_keys": user_api_keys}
        return render(request, "user/api_keys_update.html", context)


@set_user_language
@login_required
def binance_guide(request):
    """View for displaying a Binance guide page."""
    return render(request, "main_service/binance_guide.html")


@set_user_language
@login_required
def support(request):
    """View for handling user support requests."""
    if request.method == "POST":
        form = SupportForm(request.POST, request.FILES)
        if form.is_valid():
            user = request.user
            support_request = form.save(commit=False)

            support_request.user_id = user.id
            support_request.save()
            request.session["form_saved_success"] = True
        else:
            request.session["form_saved_success"] = False

        # previous_page = request.META.get('HTTP_REFERER')
        return render(request, "main_service/support.html")
    return render(request, "main_service/support.html")


@set_user_language
@login_required
def redirect_to_page(request, image_name):
    user = request.user
    """ View for redirecting to a specific strategy page, after user click on strategy photo. """
    user.selected_strategy = image_name
    user.save()
    request.session["chosen_strategy"] = image_name
    return redirect("main_service:show_chosen_strategy")


@set_user_language
def index(request):
    """View for displaying the index page."""
    return render(request, "main_service/index.html")


@set_user_language
@login_required
def deposit(request):
    """View for handling user goods and added them to basket."""
    user = request.user
    if request.method == "POST":
        if "backtesting_added_to_basket" in request.POST:
            backtesting_quantity = int(request.POST.get("backtesting_quantity"))
            user.backtesting_in_basket += backtesting_quantity
            user.total_amount_to_pay += backtesting_quantity * BACKTEST_COST
            user.save()
        elif "optimization_added_to_basket" in request.POST:
            optimization_quantity = int(request.POST.get("optimization_quantity"))
            user.optimization_in_basket += optimization_quantity
            user.total_amount_to_pay += optimization_quantity * OPTIMIZATION_COST
            user.save()

    return render(request, "user/deposit.html")


@set_user_language
@login_required
def basket(request):
    """View for managing the user's basket."""
    user = request.user
    if request.method == "POST":
        if "remove_backtesting" in request.POST:
            user.total_amount_to_pay -= user.backtesting_in_basket * BACKTEST_COST
            user.backtesting_in_basket = 0
            user.save()
        elif "remove_optimization" in request.POST:
            user.total_amount_to_pay -= user.optimization_in_basket * OPTIMIZATION_COST
            user.optimization_in_basket = 0
            user.save()
    context = {
        "backtesting_in_basket": user.backtesting_in_basket,
        "optimization_in_basket": user.optimization_in_basket,
        "total_amount_to_pay": user.total_amount_to_pay,
    }
    return render(request, "user/basket.html", context)


@set_user_language
@login_required
def payment_history(request):
    """View for displaying user payment history."""
    return render(request, "user/payment_history.html")


@set_user_language
@login_required
def dashboard_edit(request, user_id, strategy_id):
    """View for editing user`s bot."""
    user = get_object_or_404(CustomUser, id=user_id)
    trading_bot = get_object_or_404(TradingBots, id=strategy_id, user=user)

    # Add any additional logic you need to prepare data for editing

    context = {
        "user": user,
        "trading_bot": trading_bot,
    }
    return render(request, "main_service/dashboard_edit.html", context)


def delete_bot(request, bot_id):
    """View for delete user`s bot."""
    mobile = request.GET.get('mobile')
    try:
        bot = TradingBots.objects.get(id=bot_id)
        bot.delete()
    except TradingBots.DoesNotExist:
        pass  # Handle if the bot doesn't exist
    if mobile:
        mobile = {"Done": "Bot deleted successfully"}
        return JsonResponse(mobile)
    return redirect("main_service:dashboard")


@set_user_language
@login_required
def dashboard_stop(request, strategy_id):
    """View for stop user`s bot."""

    if request.method == "GET":
        user = request.user
        # >;CG05< =0AB@>9:8 87 >?B8<878@>20==>9 AB@0B5388
        trading_bot = TradingBots.objects.get(id=strategy_id)
        strategy_name = trading_bot.strategy_name
        if strategy_name == "expo_grid" or strategy_name == "preset-expo_grid":
            data = {"bot_id": strategy_id, "close_positions": "false"}
            response = requests.post(EXPO_GRID_STOP_BOT, data=data)
            if response.status_code == 200:
                print(
                    f"Bot with id: {strategy_id}, for user {user} successfully stopped"
                )
                # 1@01>B:0 A>740==KE 40==KE
                instance = TradingBots.objects.get(id=strategy_id)
                instance.status = "stopped"
                instance.save()
            else:
                print(
                    f"Error while trying to stop bot id: {strategy_id} for user {user}"
                )
        elif strategy_name == "jumper" or strategy_name == "preset-jumper":
            data = {"bot_id": strategy_id, "close_positions": "false"}
            response = requests.post(JUMPER_STOP_BOT, data=data)
            if response.status_code == 200:
                print(
                    f"Bot with id: {strategy_id}, for user {user} successfully stopped"
                )
                # 1@01>B:0 A>740==KE 40==KE
                instance = TradingBots.objects.get(id=strategy_id)
                instance.status = "stopped"
                instance.save()
            else:
                print(
                    f"Error while trying to stop bot id: {strategy_id} for user {user}"
                )
        return redirect("main_service:dashboard")


@set_user_language
@login_required
def dashboard_stop_and_close(request, strategy_id):
    """View for stop user`s bot. And close all positions"""
    if request.method == "GET":
        user_id = request.user.id
        trading_bot = TradingBots.objects.get(id=strategy_id)

        # >;CG05< >1J5:B OptimizedStrategies, A2O70==K9 A TradingBots
        optimized_strategy = trading_bot.optimized_strategy
        api_key, api_secret = get_curent_user_api_credentials(request)
        client = get_binance_client(api_key, api_secret)
        positions = client.futures_position_information()
        position_amt = float(
            [
                position["positionAmt"]
                for position in positions
                if position["symbol"] == trading_bot.trading_pair
            ][0]
        )
        if position_amt > 0:
            side = "SELL"
        elif position_amt < 0:
            side = "BUY"
        else:
            raise "Error position_amt is 0"

        url = os.getenv("F1_BOT_URL_STOP_BOT_PROD")
        # url = os.getenv("F1_BOT_URL_STOP_BOT_TEST")
        data = {
            "bot_id": optimized_strategy.id,
            "close_positions": False,
            "user_id": user_id,
            "symbol": trading_bot.trading_pair,
            "side": side,
            "quantity": abs(position_amt),
        }

        requests.post(url, data=data)
        # response = requests.post(url)
        instance = TradingBots.objects.get(id=strategy_id)
        instance.status = "inactive"
        instance.save()
        if request.user.is_staff:
            return redirect("main_service:admin_dashboard")
        return redirect("main_service:dashboard")


def backtest_optimization_start_bot(request):
    user = request.user
    chosen_strategy = request.chosen_strategy
    optimized_data = OptimizedStrategies.objects.filter(user_id=user.id, strategy=chosen_strategy).last()
    optimized_settings = optimized_data.optimized_settings

    return JsonResponse(optimized_settings)


@set_user_language
@login_required
def dashboard_details(request, user_id, strategy_id):
    user = get_object_or_404(CustomUser, id=user_id)
    trading_bot = get_object_or_404(TradingBots, id=strategy_id, user=user)

    # Add any additional logic you need to prepare data for editing
    this_bot = TradingBots.objects.get(id=strategy_id)
    this_bot_total_pnl = (
        BotsStatistic.objects.filter(user_id=user_id, trading_bot=strategy_id)
        .order_by("-id")
        .aggregate(total_pnl=Sum("realized_pnl"))
    )
    if this_bot_total_pnl["total_pnl"] is None:
        this_bot_total_pnl["total_pnl"] = 0
    this_bot_stats = BotsStatistic.objects.filter(
        user_id=user_id, trading_bot=strategy_id
    ).reverse()

    context = {
        "total_pnl": round(this_bot_total_pnl["total_pnl"], 5),
        "user": user,
        "trading_bot": trading_bot,
        "pair": this_bot.trading_pair,
        "this_bot_stats": reversed(this_bot_stats),
    }
    return render(request, "main_service/dashboard_details.html", context)


@set_user_language
@login_required
def get_dashboard_info(request):
    (
        current_user_bots,
        current_user_archive,
        invested_amount,
        stats_profit,
        pnl_percent,
    ) = ([], [], 0, 0, 0)

    user = request.user
    user_obj = BinanceApiCredentials.objects.filter(user_id=user.id)
    if user_obj:
        salt = base64.b64decode(os.getenv("KEY_SALT"))
        aes = AESCipher(salt)

        user_account_balance = round(
            get_available_balance_binance_futures(
                aes.decrypt(user_obj[0].hashed_api_key),
                aes.decrypt(user_obj[0].hashed_secret_key),
            ),
            2,
        )

        trading_bots = TradingBots.objects.all()
        for trading_bot in trading_bots:
            if trading_bot.status != 'stopped':
                days = (timezone.now() - trading_bot.launch_date).days
                hours = (timezone.now() - trading_bot.launch_date).seconds // 3600
                trading_bot.running_time = f"{days} d : {hours} h"
                trading_bot.save()

            if trading_bot.user == user:
                current_bot_stats = (
                    BotsStatistic.objects.filter(
                        user_id=user.id, trading_bot=trading_bot.id
                    )
                    .order_by("-id")
                    .aggregate(total_pnl=Sum("realized_pnl"))
                )
                if trading_bot.profit == 0:
                    pnl_percent = 0
                else:
                    pnl_percent = round(
                        trading_bot.profit * 100 / trading_bot.investment_amount, 2
                    )
                # >;CG5=85 A;>20@O 7=0G5=89 0B@81CB>2 >1J5:B0 TradingBots
                trading_bot_data = {
                    "id": trading_bot.id,
                    "strategy_name": trading_bot.strategy_name,
                    "exchange": trading_bot.exchange,
                    "trading_pair": trading_bot.trading_pair,
                    "leverage": trading_bot.leverage,
                    "margin_type": trading_bot.margin_type,
                    "investment_amount": trading_bot.investment_amount,
                    "running_time": trading_bot.running_time,
                    "pnl_percent": pnl_percent,
                    "profit": round(trading_bot.profit, 2),
                    # >102LB5 >AB0;L=K5 0B@81CBK, :>B>@K5 2K E>B8B5 2:;NG8BL
                }

                # >102;5=85 40==KE 2 A?8A>:
                if trading_bot.status == "started":
                    current_user_bots.append(trading_bot_data)
                else:
                    current_user_archive.append(trading_bot_data)

                invested_amount += trading_bot.investment_amount

                if current_bot_stats["total_pnl"] is not None:
                    trading_bot.profit = round(float(current_bot_stats["total_pnl"]), 2)
                    trading_bot.approximately_price_year = round(
                        float(current_bot_stats["total_pnl"]) * 12, 2
                    )
                    trading_bot.save()

        # @5>1@07>20=85 A?8A:0 2 D>@<0B JSON
        current_user_archive_json = json.dumps(current_user_archive)
        current_user_bots_json = json.dumps(current_user_bots)

        bot_stats = (
            BotsStatistic.objects.filter(user_id=user.id)
            .order_by("-id")
            .aggregate(total_pnl=Sum("realized_pnl"))
        )
        if bot_stats["total_pnl"] is not None:
            stats_profit = round(bot_stats["total_pnl"], 2)
            if stats_profit is None:
                stats_profit = 0

            stats_total = round(stats_profit, 2) + round(invested_amount, 2)
            if invested_amount != 0:
                summary_total = round(
                    round(stats_profit, 2) * 100 / round(invested_amount, 2), 2
                )
            else:
                summary_total = 0
        total_balance = round(user_account_balance + invested_amount, 2)
        result = {
            "current_user_archive_bots": current_user_archive_json,
            "current_user_trading_bots": current_user_bots_json,
            "total_balance": total_balance,
            "invested_amount": round(invested_amount, 2),
            "available_balance": round(user_account_balance, 2),
            "active_ats": len(current_user_bots),
            "current_profit": stats_profit,
        }

        return JsonResponse(result)
    error = {"error": "db not contains user credentials for this exchange"}
    return JsonResponse(error)


@set_user_language
@login_required
def dashboard(request):
    stats_start, stats_profit, stats_total, summary_total = 0, 0, 0, 0
    not_closed_position, binance_permissions, duplicate_symbol_started_bot = (
        False,
        False,
        False,
    )
    # user_have_enough_money = True
    current_user_bots, current_active_bots = [], []
    user = request.user

    """
        Check if user have permissions for trade on Binance    
    """
    # a = get_account_api_permissions()

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
        View for the user's dashboard.
    """
    if request.method == "POST":
        if "total_investment" in request.POST:
            pass

    trading_bots = TradingBots.objects.all().order_by("-launch_date")
    for trading_bot in trading_bots:
        if trading_bot.status != 'stopped':
            days = (timezone.now() - trading_bot.launch_date).days
            hours = (timezone.now() - trading_bot.launch_date).seconds // 3600
            trading_bot.running_time = f"{days} d : {hours} h"
            trading_bot.save()
        if trading_bot.user == user:
            current_bot_stats = (
                BotsStatistic.objects.filter(
                    user_id=user.id, trading_bot=trading_bot.id
                )
                .order_by("-id")
                .aggregate(total_pnl=Sum("realized_pnl"))
            )

            if current_bot_stats["total_pnl"] is not None:
                trading_bot.profit = round(float(current_bot_stats["total_pnl"]), 2)
                trading_bot.approximately_price_year = round(
                    float(current_bot_stats["total_pnl"]) * 12, 2
                )
                trading_bot.save()
            if trading_bot.status == "started":
                stats_start += trading_bot.investment_amount
                current_active_bots.append(trading_bot)
            else:
                current_user_bots.append(trading_bot)
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
        summary_total = round(round(stats_profit, 2) * 100 / round(stats_start, 2), 2)
    else:
        summary_total = 0

    try:
        not_closed_position = request.session.get("not_closed_position_or_orders")
    except:
        print("not_closed_position_or_orders = False")
    """new"""
    """getting user status"""
    user_status = UserStatus.objects.filter(user_id=user.id)[0]
    status_id = user_status.status_id
    status = Statuses.objects.filter(id=status_id)[0].status

    subs_days_left = user_status.expiration_date - datetime.datetime.now(pytz.utc)

    context = {
        "current_user_active_trading_bots": current_active_bots,
        "current_user_trading_bots": current_user_bots,
        "count_of_bots": len(current_active_bots),
        "stats_start": stats_start,
        "stats_profit": stats_profit,
        "stats_total": stats_total,
        "summary_total": summary_total,
        "not_closed_position_or_orders": not_closed_position,
        "user_subscription": status,
        "subscription_days_left": subs_days_left.days,
    }
    request.session["user_have_enough_money"] = True
    request.session["not_closed_position_or_orders"] = False
    return render(request, "user/dashboard.html", context)


@set_user_language
@login_required
def ai_optimizer(request):
    return render(request, "main_service/ai_optimizer.html")


# Quick start new logic update
@set_user_language
@login_required
def get_last_preset_data(request, symbol, exchange):
    result = BacktestAndOptimizationHistory.objects.filter(strategy__startswith='preset-', asset=symbol,
                                                           exchange=exchange.lower()).last()
    leverage = result.data.get('LEVERAGE') or result.data.get('leverage')
    balance = result.data.get('INITIAL BALANCE') or result.data.get('Initial balance')
    result = {
        "leverage": leverage,
        "total_investment": balance,
    }

    return JsonResponse(result)


# 58-archiveAndLaboratoryProgressbar
@set_user_language
@login_required
def get_progress_data(request):
    user = request.user
    all_items = BacktestAndOptimizationHistory.objects.filter(user_id=user.id)
    serialized_data = serializers.serialize('json', all_items)
    return JsonResponse({'items': serialized_data})



@set_user_language
@login_required
def get_last_data_id(request):
    user = request.user
    strategy = BacktestAndOptimizationHistory.objects.filter(user_id=user.id).last()
    return JsonResponse({'strategyID': strategy.id})
# 58-archiveAndLaboratoryProgressbar


# 60-DataFromOptimizer
def update_optimization_data(request):
    backtest_and_optimization_id = request.GET.get('backtest_and_optimization_id')
    result = request.GET.get('result', None)
    if result:
        result = json.loads(result)
    try:
        backtest_and_optimization_strategy = BacktestAndOptimizationHistory.objects.get(id=backtest_and_optimization_id)
        if result:
            pnl = 0
            if result['CHOSEN STRATEGY'] == 'expo_grid' or result['CHOSEN STRATEGY'] == 'preset-expo_grid':
                pnl = '{:.2f}'.format(100 * result['AVAILABLE BALANCE'] / result['INITIAL BALANCE'] - 100)

            if result['CHOSEN STRATEGY'] == 'jumper' or result['CHOSEN STRATEGY'] == 'preset-jumper':
                pnl = '{:.2f}'.format(100 * result['END BALANCE'] / result['INVESTMENT'] - 100)

            backtest_and_optimization_strategy.data = result
            backtest_and_optimization_strategy.status = 'success'
            backtest_and_optimization_strategy.pnl = pnl
            backtest_and_optimization_strategy.asset = result['ASSET']
            finish = backtest_and_optimization_strategy.final_progress_number
            backtest_and_optimization_strategy.progress = finish
            backtest_and_optimization_strategy.save()
        else:
            final_progress_number = request.GET.get('final_progress_number')
            progress = request.GET.get('progress')
            backtest_and_optimization_strategy.final_progress_number = final_progress_number
            backtest_and_optimization_strategy.progress = progress
            backtest_and_optimization_strategy.status = 'processing'
            backtest_and_optimization_strategy.save()

        return JsonResponse({'status': 'updated'})

    except BacktestAndOptimizationHistory.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': 'Backtest and optimization history not found'})

    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})
# 60-DataFromOptimizer

@set_user_language
@login_required
def profile(request):
    """
    View for user profile management.
    """
    user = request.user
    user_id = str(user.id)[:10]
    # Creating a verification_code for catching it after user
    # clicked an url in email verification letter.
    statuses = Statuses.objects.all()

    if statuses:
        trial = statuses[0]
        basic = statuses[1]
        pro = statuses[2]
        vip = statuses[3]
        user_stats = UserStatus.objects.filter(user_id=user.id)
        if user_stats:
            user_stats = user_stats[0]
        else:
            auto_setting_of_trial_status(user)
            user_stats = UserStatus.objects.filter(user_id=user.id)[0]
        user_status = user_stats.status.status
        user_expired_date = user_stats.expiration_date
        time_left = (
                user_expired_date - datetime.datetime.now(datetime.timezone.utc)
        ).days
        # 230-AccountStatusChecking
        if time_left < 0:
            if user.num_of_backtesting != 0:
                user.num_of_backtesting = 0
            if user.num_of_optimization != 0:
                user.num_of_optimization = 0
            if user.num_of_ats != 0:
                user.num_of_ats = 0
            user.save()
        # 230-AccountStatusChecking
    else:
        print("model Statuses doesnt contains any status")
    if not user.verification_code:
        user.verification_code = secrets.token_hex(16)
        user.save()

    context = {
        "email_verified": user.email_verified,
        "num_of_backtesting": user.num_of_backtesting,
        "num_of_optimization": user.num_of_optimization,
        "user_id": user_id,
        "trial": trial,
        "basic": basic,
        "pro": pro,
        "vip": vip,
        "user_status": user_status,
        "user_expired_date": user_expired_date,
        "time_left": time_left,
        "backtest_left": user.num_of_backtesting,
        "optimization_left": user.num_of_optimization,
        "ats_left": user.num_of_ats,
        "bybit_keys_changed": request.session.get("bybit_keys_changed"),
        "bybit_permissions": request.session.get("bybit_permissions"),
        "binance_keys_changed": request.session.get("binance_keys_changed"),
        "binance_permissions": request.session.get("binance_permissions"),
        'bybit_keys_changing_exception': request.session.get("bybit_keys_changing_exception"),
        'binance_keys_changing_exception': request.session.get("binance_keys_changing_exception")
        # "ats": user_status.get("max_ats_count"),
        # "backtest": user_status.get("max_backtests"),
        # "optimization": user_status.get("max_optimizations")
    }
    print(context['bybit_keys_changed'])
    print(context['binance_keys_changed'])
    request.session['bybit_keys_changed'] = False
    request.session['binance_keys_changed'] = False
    request.session['bybit_keys_changing_exception'] = False
    request.session['binance_keys_changing_exception'] = False
    if request.method == "POST":
        if "personal_data" in request.POST:
            context["personal_data"] = True
            context["user"] = user
        if "save_phone_number" in request.POST:
            context["personal_data"] = True
        if "save_email" in request.POST:
            user.email = request.POST.get("email")
            user.save()
            context["personal_data"] = True
        if "verification" in request.POST:
            context["verification"] = True
            # if "verify_email" in request.POST:
            #     status_code = email_sender(user.email)
            #     if 200 <= status_code <= 202:
            #         context["email_sent"] = True
        if "trading_bot_dashboard" in request.POST:
            context["trading_bot_dashboard"] = True
        if "available_instruments" in request.POST:
            context["available_instruments"] = True
            if "payment_history" in request.POST:
                return redirect("main_service:payment_history")
            if "deposit_usd" in request.POST:
                return render(request, "user/deposit.html")

    return render(request, "user/profile.html", context)


@set_user_language
@login_required
def email_confirmation(request, verification_code):
    """
    View for email confirmation.
    """
    context = {"email_verified": False}
    try:
        user = get_user_model().objects.get(verification_code=verification_code)
        user.email_verified = True
        user.save()
        context["email_verified"] = True
        return render(request, "main_service/index.html", context)
    except get_user_model().DoesNotExist:
        return render(request, "main_service/index.html", context)


@set_user_language
@login_required
def trading_description(request):
    context = {}
    exception = ""
    """
    View for trading description, managing
     of optimized data, available to see, download settings, or create the bot.
    """
    result_permissions = {"permissions": []}
    same_users = False
    user = request.user
    try:
        items = BinanceApiCredentials.objects.filter(user_id=user.id)
        for x in items:
            user_id = x.user_id
            same_users = user_id == user.id
            result_permissions = x.permissions
        if same_users:
            context = {
                "binance_keys_saved": True,
                "binance_permissions": result_permissions["permissions"],
            }
        else:
            context = {"binance_keys_saved": False}
    except:
        print(f"BinanceApiCredentials has no data for user {user}")

    if request.method == "POST":
        if "description" in request.POST:
            # save after artificial intelligent optimizer setting for each user in own folder symbol, interval, total investment 50 by default
            instance = (
                OptimizedStrategies.objects.filter(user_id=user.id) # strategy=strategy
                .order_by("-id")
                .first()
            )
            data_dict = instance.json_data
            # ISOLATED, CROSSED
            user_dict = {
                "symbol": data_dict["symbol"],
                "interval": data_dict["interval"],
                "total_investment": 50,
                "leverage": 1,
                "margin_type": "ISOLATED",
            }

            directory_path = os.path.join(
                os.getcwd(),
                "trading_bots",
                "users_settings",
                str(user),
                str(user.selected_strategy),
            )
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)
            with open(
                    os.path.join(directory_path, f"{user.selected_strategy}.json"), "w"
            ) as file:
                json.dump(user_dict, file)
        if (
                "api_key" in request.POST
                and "api_secret" in request.POST
                and context["binance_keys_saved"] is not True
        ):
            binance_api_key = request.POST.get("api_key")
            binance_secret_key = request.POST.get("api_secret")
            ex = False
            try:
                permissions = get_account_api_permissions(
                    binance_api_key, binance_secret_key
                )
            except Exception as ex:
                # if ex.code == -1022:
                #     exception = "Invalid API or secret keys."
                # elif ex.code == -2015:

                context = {"ex": ex.code, "binance_keys_saved": False}
                return render(request, "trading/trading_description.html", context)

            if permissions:
                client = Client(api_key, api_secret)
                account_info = client.get_account_api_permissions()
                if account_info.get(
                        'enableWithdrawals'
                ) or account_info.get(
                    'enableInternalTransfer'
                ) or account_info.get(
                    'permitsUniversalTransfer'
                ):
                    ex = f"Dexima ATS not allowed api keys which has a permissions for Withdraw of any type " \
                         f"of transfer funds, uncheck all point which contain this permissions"
                    context = {
                        "binance_keys_saved": False,
                        "ex": ex,
                    }
                    return render(request, "trading/trading_description.html", context)
                if permissions["spot"]:
                    result_permissions["permissions"].append("SPOT")
                if permissions["margin"]:
                    result_permissions["permissions"].append("MARGIN")
                if permissions["futures"]:
                    result_permissions["permissions"].append("FUTURES")

                salt = base64.b64decode(os.getenv("KEY_SALT"))
                aes = AESCipher(salt)
                hashed_api_key = aes.encrypt(binance_api_key)
                hashed_secret_key = aes.encrypt(binance_secret_key)
                print(aes.decrypt(hashed_api_key))
                print(aes.decrypt(hashed_secret_key))
                instance = BinanceApiCredentials()
                instance.hashed_api_key = hashed_api_key
                instance.hashed_secret_key = hashed_secret_key
                instance.permissions = result_permissions
                instance.user_id = user.id
                instance.save()
                request.session["binance_keys_saved"] = True
                context = {
                    "binance_keys_saved": True,
                    "binance_permissions": result_permissions["permissions"],
                    "ex": ex,
                }
                return render(request, "trading/trading_description.html", context)
            else:
                context = {"binance_permissions": False}
                return render(request, "trading/trading_description.html", context)

        if "check_permissions_again" in request.POST:
            context = {"binance_keys_saved": False}
            if BinanceApiCredentials.objects.filter(user_id=user.id):
                BinanceApiCredentials.objects.filter(user_id=user.id).delete()

    return render(request, "trading/trading_description.html", context)


@set_user_language
@login_required
def trading_description_bybit(request):
    context = {}
    exception = ""
    """
    View for trading description, managing
     of optimized data, available to see, download settings, or create the bot.
    """
    result_permissions = {"permissions": []}
    same_users = False
    user = request.user
    try:
        items = BybitApiCredentials.objects.filter(user_id=user.id)
        for x in items:
            user_id = x.user_id
            same_users = user_id == user.id
            result_permissions = x.permissions
        if same_users:
            context = {
                "bybit_keys_saved": True,
                "bybit_permissions": result_permissions["permissions"],
            }
        else:
            context = {"bybit_keys_saved": False}
    except:
        print(f"BybitApiCredentials has no data for user {user}")

    if request.method == "POST":
        if "description" in request.POST:
            # save after artificial intelligent optimizer setting for each user in own folder symbol, interval, total investment 50 by default
            instance = (
                OptimizedStrategies.objects.filter(user_id=user.id) # strategy=strategy
                .order_by("-id")
                .first()
            )
            data_dict = instance.json_data
            # ISOLATED, CROSSED
            user_dict = {
                "symbol": data_dict["symbol"],
                "interval": data_dict["interval"],
                "total_investment": 50,
                "leverage": 1,
                "margin_type": "ISOLATED",
            }

            directory_path = os.path.join(
                os.getcwd(),
                "trading_bots",
                "users_settings",
                str(user),
                str(user.selected_strategy),
            )
            if not os.path.exists(directory_path):
                os.makedirs(directory_path)
            with open(
                    os.path.join(directory_path, f"{user.selected_strategy}.json"), "w"
            ) as file:
                json.dump(user_dict, file)
        if (
                "api_key" in request.POST
                and "api_secret" in request.POST
                and context["bybit_keys_saved"] is not True
        ):
            bybit_api_key = request.POST.get("api_key")
            bybit_secret_key = request.POST.get("api_secret")
            ex = False
            try:
                permissions = get_account_api_permissions_bybit(
                    bybit_api_key, bybit_secret_key
                )
            except Exception as ex:
                # if ex.code == -1022:
                #     exception = "Invalid API or secret keys."
                # elif ex.code == -2015:
                if ex.status_code == 10010:
                    context = {"ex": ex.message, "bybit_keys_saved": False}
                else:
                    context = {"ex": ex, "bybit_keys_saved": False}
                return render(
                    request, "trading/trading_description_bybit.html", context
                )
            if permissions:
                session = HTTP(
                    testnet=False,
                    api_key=bybit_api_key,
                    api_secret=bybit_secret_key,
                )
                data = session.get_api_key_information()["result"]["permissions"]
                if data['Wallet'] or data['Exchange']:
                    ex = f"Dexima ATS not allowed api keys which has a permissions for Withdraw of any type " \
                         f"of transfer funds, uncheck all point which contain this permissions"
                    context = {
                        "bybit_keys_saved": False,
                        "ex": ex,
                    }
                    return render(request, "trading/trading_description_bybit.html", context)
                if permissions["spot"]:
                    result_permissions["permissions"].append("SPOT")
                if permissions["derivatives"]:
                    result_permissions["permissions"].append("Derivatives")

                salt = base64.b64decode(os.getenv("KEY_SALT"))
                aes = AESCipher(salt)
                hashed_api_key = aes.encrypt(bybit_api_key)
                hashed_secret_key = aes.encrypt(bybit_secret_key)
                print(aes.decrypt(hashed_api_key))
                print(aes.decrypt(hashed_secret_key))
                instance = BybitApiCredentials()
                instance.hashed_api_key = hashed_api_key
                instance.hashed_secret_key = hashed_secret_key
                instance.permissions = result_permissions
                instance.user_id = user.id
                instance.save()
                request.session["bybit_keys_saved"] = True
                context = {
                    "bybit_keys_saved": True,
                    "bybit_permissions": result_permissions["permissions"],
                    "ex": ex,
                }
                return render(
                    request, "trading/trading_description_bybit.html", context
                )
            else:
                context = {"bybit_permissions": False}
                return render(
                    request, "trading/trading_description_bybit.html", context
                )

        if "check_permissions_again" in request.POST:
            context = {"bybit_keys_saved": False}
            if BybitApiCredentials.objects.filter(user_id=user.id):
                BybitApiCredentials.objects.filter(user_id=user.id).delete()

    return render(request, "trading/trading_description_bybit.html", context)


def confirm_email(request, user_pk, email_hash, token):
    try:
        user_id = urlsafe_base64_decode(user_pk).decode()
        user = CustomUser.objects.get(id=user_id)
    except (TypeError, ValueError, OverflowError, CustomUser.DoesNotExist):
        return HttpResponseBadRequest("Invalid request parameters.")

    if user.is_active:
        response = HttpResponse("""
            <html>
                <head>
                    <meta http-equiv="refresh" content="5;url=/" />
                </head>
                <body>
                    This link has already been used. You will be redirected to the main page.
                </body>
            </html>
        """)
        return response

    if hashlib.md5(user.email.encode()).hexdigest() != email_hash:
        return HttpResponseBadRequest("Invalid email hash.")

    if user.verification_code != token:
        return HttpResponseBadRequest("Invalid token.")

    user.email_verified = True
    user.is_active = True
    user.save()

    login(request, user)
    return redirect("main_service:index")


def generate_confirmation_link(user, token):
    BASE_URL = "http://195.201.70.92"
    django_endpoint = BASE_URL + ":80"
    email_hash = hashlib.md5(user.email.encode()).hexdigest()
    confirmation_link = f"{django_endpoint}/confirm/{urlsafe_base64_encode(force_bytes(user.pk))}/{email_hash}/{token}/"
    return confirmation_link


@set_user_language
def register_request(request):
    if request.method == "POST":
        form = NewUserForm(request.POST)
        try:
            if form.is_valid():
                user = form.save()

                token = secrets.token_hex(16)
                user.verification_code = token
                user.save()

                confirmation_link = generate_confirmation_link(user, token)
                tasks.send_confirmation_email.delay(user.email, confirmation_link)

                message = f'Dear {user.username}, open your mail and click the link to verify your email address to complete registration.'
                cache_key = f'registration_message_{user.username}'
                cache.set(cache_key, message, 70000)
                request.session['registration_message_key'] = cache_key

                return redirect("main_service:index")
            else:
                # A;8 D>@<0 =5 20;84=0, 4>102LB5 A>>1I5=8O >1 >H81:0E.
                if "username" in form.errors:
                    messages.error(request, "Username is already taken.")
                if "email" in form.errors:
                    messages.error(request, "Email address is already in use.")
        except Exception as ex:
            print(ex)
    else:
        form = NewUserForm()

    return render(
        request=request,
        template_name="registration/register.html",
        context={"register_form": form},
    )


@set_user_language
@login_required
def add_to_dashboard(request):
    print("add_to_dashboard_start")
    user = request.user
    data = json.loads(request.GET["requestData"])
    if request.method == "GET":
        chosen_strategy = data.get("chosen_strategy").lower()
        chosen_exchange = data.get("chosen_exchange").lower()
        chosen_asset = data.get("chosen_asset")
        total_investment = float(data.get("total_investment", 1000))
        leverage = int(data.get("leverage", 1))
        # margin_type = request.GET.get("margin_type", "ISOLATED")
        custom_user = get_object_or_404(CustomUser, id=user.id)
        current_time = timezone.now()
        if chosen_strategy == "expo_grid" or chosen_strategy == "preset-expo_grid":
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
            trading_bot.margin_type = "ISOLATED"
            trading_bot.save()
            bot_id = trading_bot.id

            optimized_data = OptimizedStrategies.objects.filter(
                user_id=user.id, strategy=chosen_strategy,
                json_data__contains={"ASSET": chosen_asset}, exchange=chosen_exchange).last()

            data = {
                "bot_id": bot_id,
                "user_id": request.user.id,
                "symbol": chosen_asset,
                "available_balance": total_investment,
                "leverage": leverage,
                "num_of_grids": optimized_data.optimized_settings["NUM OF GRIDS"],
                "timeframe": optimized_data.optimized_settings["TIMEFRAME"],
                "price_range": optimized_data.optimized_settings["PRICE RANGE"],
                "activation_trigger_in_percent": optimized_data.optimized_settings[
                    "ACTIVATION TRIGGER IN PERCENT"
                ],
                "distribution_of_grid_lines": optimized_data.optimized_settings[
                    "DISTRIBUTION OF GRID LINES"
                ],
                "line_disbalance_direction": optimized_data.optimized_settings[
                    "LINE DISBALANCE DIRECTION"
                ],
                "short_stop_loss_in_percent": optimized_data.optimized_settings[
                    "SHORT STOP LOSS IN PERCENT"
                ],
                "long_stop_loss_in_percent": optimized_data.optimized_settings[
                    "LONG STOP LOSS IN PERCENT"
                ],
                "grid_disbalance_direction": optimized_data.optimized_settings[
                    "GRID DISBALANCE DIRECTION"
                ],
                "trend_period_timeframe": optimized_data.optimized_settings[
                    "TREND PERIOD TIMEFRAME"
                ],
                "trend_period": optimized_data.optimized_settings["TREND PERIOD"],
                # "margin_type": margin_type,
            }

            response = requests.post(EXPO_GRID_START_BOT, data=data)
            if response.status_code == 200:
                print("Grid bot started!")
                trading_bot.status = "started"
                trading_bot.save()
            else:
                print(
                    f"H81:0 ?@8 70?CA:5 grid 1>B0. >4 A>AB>O=8O: {response.status_code}"
                )

            return redirect("main_service:dashboard")
        elif chosen_strategy == "jumper" or chosen_strategy == "preset-jumper":
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
            trading_bot.margin_type = "ISOLATED"
            trading_bot.save()
            bot_id = trading_bot.id

            optimized_data = OptimizedStrategies.objects.filter(
                user_id=user.id, strategy=chosen_strategy,
                json_data__contains={"ASSET": chosen_asset}, exchange=chosen_exchange).last()

            data = {
                "bot_id": bot_id,
                "user_id": request.user.id,
                "symbol": chosen_asset,
                "available_balance": total_investment,
                "leverage": leverage,
                "long_entry_sum_in_dollars": optimized_data.optimized_settings[
                    "AMOUNT FOR LONG"
                ],
                "short_entry_sum_in_dollars": optimized_data.optimized_settings[
                    "AMOUNT FOR SHORT"
                ],
                "long_take_profit_percent": optimized_data.optimized_settings[
                    "LONG TP %"
                ],
                "long_stop_loss_percent": optimized_data.optimized_settings[
                    "LONG SL %"
                ],
                "short_take_profit_percent": optimized_data.optimized_settings[
                    "SHORT TP %"
                ],
                "short_stop_loss_percent": optimized_data.optimized_settings[
                    "SHORT SL %"
                ],
                "price_difference_long_entry": optimized_data.optimized_settings[
                    "LONG DIVERGENCE %"
                ],
                "price_difference_short_entry": optimized_data.optimized_settings[
                    "SHORT DIVERGENCE %"
                ],
                "block_long_trade_until": None,
                "block_short_trade_until": None,
                "long_pause_after_trade_min": optimized_data.optimized_settings[
                    "LONG PAUSE MINUTE"
                ],
                "short_pause_after_trade_min": optimized_data.optimized_settings[
                    "SHORT PAUSE MINUTE"
                ],
                "order_expiration_by_price_percent_limit": optimized_data.optimized_settings[
                    "PRICE CHANGE LIMIT %"
                ],
                "short_period": optimized_data.optimized_settings["SHORT PERIOD"],
                "long_period": optimized_data.optimized_settings["LONG PERIOD"],
                "LEVERAGE": leverage,
                "long_trailing_stop": optimized_data.optimized_settings[
                    "LONG TRAILING STOP"
                ],
                "short_trailing_stop": optimized_data.optimized_settings[
                    "SHORT TRAILING STOP"
                ],
            }
            response = requests.post(JUMPER_START_BOT, data=data)
            if response.status_code == 200:
                print("Jumper bot started!")
                trading_bot.status = "started"
                trading_bot.save()
            else:
                print(
                    f"H81:0 ?@8 70?CA:5 jumper 1>B0. >4 A>AB>O=8O: {response.status_code}"
                )

            return redirect("main_service:dashboard")


@timing_decorator
def get_minimal_quantity(request, symbol):
    minimal_qty_for_trade, symbol_info, current_symbol_price = asyncio.run(
        get_right_minimal_investment_for_each_symbol(symbol)
    )

    minimal_qty_for_trade += minimal_qty_for_trade / 10

    current_symbol_price = asyncio.run(get_current_price(symbol))

    # symbol_info = get_symbol_info(symbol)
    min_qty = calculate_min_quantity(symbol_info)
    if min_qty >= 1:
        value_to_round = 0
    else:
        value_to_round = int(-1 * round(math.log10(min_qty)))

    min_investment = round(minimal_qty_for_trade * current_symbol_price, value_to_round)
    max_leverage = asyncio.run(get_max_leverage(symbol, api_key, api_secret))
    # max_leverage = 20

    max_investment = 1000
    min_leverage = 1

    data = {
        "min_total": min_investment,
        "max_total": max_investment,
        "min_leverage": min_leverage,
        "max_leverage": max_leverage,
    }
    return JsonResponse(data)


def backtest_and_optimization_history(request):
    user = request.user
    history = BacktestAndOptimizationHistory.objects.filter(user_id=user.id).order_by(
        "-date"
    )
    context = {"history": history}
    return render(request, "history/backtest_and_optimization_history.html", context)


def get_market(request):
    data = {"markets": ["crypto", "stock"]}
    return JsonResponse(data)


def get_exchange(request, market):
    if market == "crypto":
        data = {"exchanges": ["Binance", "Bybit", "KuCoin"]}
    elif market == "stock":
        data = {"exchanges": ["InteractiveBrokers", "Metatrader"]}
    else:
        data = {"exchanges": []}
    return JsonResponse(data)


def get_asset(request, exchange):
    if exchange.lower() == "binance":
        table_name = "assets"
        column_name = "asset"
        with connections["postgres_data"].cursor() as cursor_postgres:
            cursor_postgres.execute(f"SELECT {column_name} FROM {table_name}")

            assets_tuples = cursor_postgres.fetchall()
        assets = [asset[0] for asset in assets_tuples]
        data = {"assets": assets}
    elif exchange == "Bybit":
        assets = []
        data = {"assets": assets}
    elif exchange == "KuCoin":
        assets = []
        data = {"assets": assets}
    else:
        data = {"assets": []}
    return JsonResponse(data)


# use get_minimal_quantity for amount, leverage, margin_type


def get_strategy(request, exchange):
    if exchange.lower() == "binance":
        data = {"strategies": ["f1", "futures_grid_bot", "grid_bot"]}
    else:
        data = {"strategies": []}
    return JsonResponse(data)


def get_default_settings(request, strategy):
    file_path = os.getcwd() + "/source/strategies.json"
    with open(file_path, "r") as file:
        # Load the JSON content
        strategies_data = json.load(file)
    if strategy.lower() == "f1":
        data = {"settings": strategies_data["f1"]}
    elif strategy.lower() == "futures_grid_bot":
        data = {"settings": strategies_data["futures_grid_bot"]}
    elif strategy.lower() == "grid_bot":
        data = {"settings": strategies_data["grid_bot"]}
    else:
        data = {"strategies": []}
    return JsonResponse(data)


def mobile_dashboard(request):
    return render(request, "main_service/dashboard.html")


"""
  # "num_of_grids": [10, 20, 30, 40, 50, 60, 70, 80, 90, 100],
        # "timeframe": ["1m", "5m", "15m", "30m", "1h", "2h", "4h", "1d"],
        # "price_range": [12, 22, 32, 42, 52, 62, 72],
        # "activation_trigger_in_percent": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
        # "distribution_of_grid_lines": ["LINEAR", "FIBONACCI"],
        # "line_disbalance_direction": ["ASCENDING", "DESCENDING"],
        # "short_stop_loss_in_percent": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
        # "long_stop_loss_in_percent": [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0],
        # "grid_disbalance_direction": ["ASCENDING", "DESCENDING"],
        # "trend_period_timeframe": ["1m", "1h", "1d"],
        # "trend_period": [12, 22, 32, 42, 52, 62, 72]
"""


def get_bybit_expo_grid_bot_settings(request):
    params = get_bybit_settings()
    return JsonResponse(params)


def get_jumper_bot_settings(request):
    params = get_jumper_settings()
    return JsonResponse(params)


def get_bybit_open_order_rules(request):
    symbol = request.GET["symbol"]
    result = asyncio.run(get_right_minimal_investment_bybit(symbol))
    return JsonResponse(result)


def get_bybit_backtest_and_optimization_params(request):
    if request.method == "GET":
        try:
            user = request.user
            backtest_result = backtest_and_optimize_request_bybit(
                    request, None, None
                )
            print(backtest_result)
            if 'Sorry' in backtest_result[0]:
                return JsonResponse({"error": 'Sorry, not enough backtests or optimizations on your account'})
            return JsonResponse(backtest_result[0])
        except Exception as e:
            # Catch exceptions and return an error
            return JsonResponse({"error": str(e)})



def delete_archive_data(request):
    if request.method == "POST":
        result = request.POST.getlist("selected_items")
        converted_to_int_result = [int(result[x]) for x in range(len(result))]
        # for int(x) in res
        BacktestAndOptimizationHistory.objects.filter(
            id__in=converted_to_int_result
        ).delete()
        return redirect("main_service:backtest_and_optimization_history")


def test_view(request):
    return render(request, "main_service/test.html")


def privacy_policy(request):
    return render(request, "documents/privacy_policy.html")


def risk_disclaimer(request):
    return render(request, "documents/risk_disclaimer.html")


from django.contrib.auth.hashers import check_password, make_password


def password_change_view(request):
    if request.method == "POST":
        current_password = request.POST.get("current_password")
        new_password = request.POST.get("new_password")

        # >;CG5=85 B5:CI53> ?>;L7>20B5;O
        user = request.user

        # @>25@:0 B5:CI53> ?0@>;O
        if check_password(current_password, user.password):
            # 5H8D@0F8O =>2>3> ?0@>;O
            hashed_password = make_password(new_password)

            # 1=>2;5=85 ?0@>;O ?>;L7>20B5;O
            user.password = hashed_password
            user.save()

            return HttpResponse("Password changed successfully!")
        else:
            return HttpResponse("Current password is incorrect.")
    else:
        return HttpResponse("Invalid request method")


def get_backtest_and_optimize_jumper_params(request):
    user = request.user
    chosen_strategy = "jumper"
    # OPTIMIZE

    if "requestData" in request.GET:
        activity = "optimize"
        json_data = json.loads(request.GET["requestData"])
        url = JUMPER_OPTIMIZATION
        from_ = json_data["from_date"]
        to = json_data["to_date"]
        data = {
            "symbol": json_data["symbol"],
            "leverage": json_data["leverage"],
            "available_balance": json_data["available_balance"],
            "from": json_data["from_date"],
            "to": json_data["to_date"],
            "data": json.dumps(json_data["data"]),
        }

    # BACKTEST
    else:
        activity = "backtest"
        url = JUMPER_BACKTEST

        data = {
            "symbol": request.GET.get("symbol"),
            "available_balance": request.GET.get("available_balance"),
            "timeframe": request.GET.get("timeframe"),
            "leverage": request.GET.get("leverage"),
            "long_entry_sum_in_dollars": request.GET.get("long_entry_sum_in_dollars"),
            "short_entry_sum_in_dollars": request.GET.get("short_entry_sum_in_dollars"),
            "long_take_profit_percent": request.GET.get("long_take_profit_percent"),
            "long_stop_loss_percent": request.GET.get("long_stop_loss_percent"),
            "short_take_profit_percent": request.GET.get("short_take_profit_percent"),
            "short_stop_loss_percent": request.GET.get("short_stop_loss_percent"),
            "price_difference_long_entry": request.GET.get(
                "price_difference_long_entry"
            ),
            "price_difference_short_entry": request.GET.get(
                "price_difference_short_entry"
            ),
            "block_long_trade_until": None,
            "block_short_trade_until": None,
            "long_pause_after_trade_min": request.GET.get("long_pause_after_trade_min"),
            "short_pause_after_trade_min": request.GET.get(
                "short_pause_after_trade_min"
            ),
            "order_expiration_by_price_percent_limit": request.GET.get(
                "order_expiration_by_price_percent_limit"
            ),
            "short_period": request.GET.get("short_period"),
            "long_period": request.GET.get("long_period"),
            "long_trailing_stop": request.GET.get("long_trailing_stop"),
            "short_trailing_stop": request.GET.get("short_trailing_stop"),
            "from": request.GET.get("from"),
            "to": request.GET.get("to"),
        }
        from_ = request.GET.get("from")
        to = request.GET.get("to")
    """1day"""
    timeout_seconds = 60 * 60 * 24
    response = requests.post(url, data=data, timeout=timeout_seconds)
    if response.status_code == 200:
        result = response.json()

        backtest_and_optimization_history_saver(
            request=request,
            data=result,
            chosen_strategy=chosen_strategy,
            activity=activity,
            from_=from_,
            to=to,
        )

        if activity == "optimize":
            custom_user = get_object_or_404(CustomUser, id=user.id)
            optimized_settings = result["SETTINGS"]

            instance = OptimizedStrategies(
                json_data=result,
                user=custom_user,
                optimized_settings=optimized_settings,
                strategy=chosen_strategy
            )
            instance.save()

        print(result)
        return JsonResponse(result)


@set_user_language
@login_required
def change_api_keys(request):
    user_id = request.user.id
    salt = base64.b64decode(os.getenv("KEY_SALT"))
    aes = AESCipher(salt)
    bybit_keys = BybitApiCredentials.objects.filter(user_id=user_id).last()
    binance_keys = BinanceApiCredentials.objects.filter(user_id=user_id).last()
    if request.method == "GET":
        keys_exist = False
        context = {}
        if bybit_keys is None and binance_keys is None:
            context["keys_exist"] = keys_exist
            return render(request, "main_service/change_api_keys.html", context)
        if bybit_keys:
            print("bybit true")
            keys_exist = True
            bybit_api_key = aes.decrypt(bybit_keys.hashed_api_key)
            first_four = bybit_api_key[:4]
            last_four = bybit_api_key[-4:]
            masked_part = '*' * 4
            masked_bybit_api_key = first_four + masked_part + last_four
            context["keys_exist"] = keys_exist
            context['bybit_api_key'] = masked_bybit_api_key
        if binance_keys:
            print("binance true")
            keys_exist = True
            binance_api_key = aes.decrypt(binance_keys.hashed_api_key)
            first_four = binance_api_key[:4]
            last_four = binance_api_key[-4:]
            masked_part = '*' * 4
            masked_binance_api_key = first_four + masked_part + last_four
            context["keys_exist"] = keys_exist
            context["binance_api_key"] = masked_binance_api_key

        return render(request, "main_service/change_api_keys.html", context)
    if request.method == "POST":
        result_permissions = {"permissions": []}
        if request.POST.get('new_bybit_api_key'):
            api_key = request.POST.get('new_bybit_api_key')
            secret_key = request.POST.get('new_bybit_secret_key')
            try:
                permissions = get_account_api_permissions_bybit(
                    api_key, secret_key
                )
            except Exception as ex:
                print(ex)
                permissions = {}
            session = HTTP(
                testnet=False,
                api_key=api_key,
                api_secret=secret_key,
            )
            data = session.get_api_key_information()["result"]["permissions"]
            if data['Wallet'] or data['Exchange']:
                ex = f"Dexima ATS not allowed api keys which has a permissions for Withdraw of any type " \
                     f"of transfer funds, uncheck all point which contain this permissions"
                request.session["bybit_keys_changed"] = False
                request.session["bybit_keys_changing_exception"] = ex
                return redirect("main_service:profile")
            if permissions["spot"]:
                result_permissions["permissions"].append("SPOT")
            if permissions["derivatives"]:
                result_permissions["permissions"].append("Derivatives")
            hashed_api_key = aes.encrypt(api_key)
            hashed_secret_key = aes.encrypt(secret_key)
            bybit_keys.hashed_api_key = hashed_api_key
            bybit_keys.hashed_secret_key = hashed_secret_key
            bybit_keys.permissions = result_permissions
            bybit_keys.save()
            request.session["bybit_keys_changed"] = True
            request.session['bybit_permissions'] = permissions
        elif request.POST.get('new_binance_api_key'):
            api_key = request.POST.get('new_binance_api_key')
            secret_key = request.POST.get('new_binance_secret_key')
            try:
                permissions = get_account_api_permissions(
                    api_key, secret_key
                )
            except Exception as ex:
                print(ex)
                permissions = {}
            client = Client(api_key, api_secret)
            account_info = client.get_account_api_permissions() #????? signature
            if account_info.get(
                    'enableWithdrawals'
            ) or account_info.get(
                'enableInternalTransfer'
            ) or account_info.get(
                'permitsUniversalTransfer'
            ):
                ex = f"Dexima ATS not allowed api keys which has a permissions for Withdraw of any type " \
                     f"of transfer funds, uncheck all point which contain this permissions"
                request.session["binance_keys_changed"] = False
                request.session["binance_keys_changing_exception"] = ex
                return redirect("main_service:profile")
            if permissions["spot"]:
                result_permissions["permissions"].append("SPOT")
            if permissions["margin"]:
                result_permissions["permissions"].append("MARGIN")
            if permissions["futures"]:
                result_permissions["permissions"].append("FUTURES")
            hashed_api_key = aes.encrypt(api_key)
            hashed_secret_key = aes.encrypt(secret_key)
            binance_keys.hashed_api_key = hashed_api_key
            binance_keys.hashed_secret_key = hashed_secret_key
            binance_keys.permissions = result_permissions
            binance_keys.save()
            request.session["binance_keys_changed"] = True
            request.session['binance_permissions'] = permissions
        return redirect("main_service:profile")


def start_trading_from_archive(request, item_id):
    if request.method == "GET":
        user = request.user
        custom_user = get_object_or_404(CustomUser, id=user.id)
        restart_bot = request.GET.get('restart_bot')

        # 233-StartTradingButtonLogicToMobileDashboardArchive
        if restart_bot:
            activity_instance = get_object_or_404(TradingBots, id=item_id)
            asset = activity_instance.trading_pair
            strategy = activity_instance.strategy_name.lower()
            exchange = activity_instance.exchange.lower()
            investment_amount = activity_instance.investment_amount
            leverage = activity_instance.leverage
        else:
            activity_instance = BacktestAndOptimizationHistory.objects.filter(id=item_id)[0]
            asset = activity_instance.asset
            strategy = activity_instance.strategy.lower()
            activity = activity_instance.activity
            exchange = activity_instance.exchange.lower()
            data = activity_instance.data
            investment_amount = float(data['INITIAL BALANCE'])
            leverage = int(data['LEVERAGE'])
        # 233-StartTradingButtonLogicToMobileDashboardArchive

        # Account_status_checking
        result = check_account_status(request)
        result_data = json.loads(result.content.decode('utf-8'))

        if not result_data['expired']:
            error_message = {"error": "Your subscription has expired"}
            return JsonResponse(error_message, status=400)

        # 228-ATSChecking
        # Available_ats_checking
        result = check_ats(request)
        result_data = json.loads(result.content.decode('utf-8'))

        if not result_data['no_ats']:
            error_message = {"error": "No more available ATS"}
            return JsonResponse(error_message, status=400)

        # API Keys checking
        result = None
        if exchange == 'binance':
            result = check_user_api_keys(request)
        elif exchange == 'bybit':
            result = check_user_api_keys_bybit(request)

        result_data = json.loads(result.content.decode('utf-8'))

        if not result_data['keys_saved']:
            error_message = {"error": "Error validating API keys"}
            return JsonResponse(error_message, status=400)

        # Balance checking
        result = check_balance(request, investment_amount)

        result_data = json.loads(result.content.decode('utf-8'))

        if not result_data['enough_balance']:
            error_message = {"error": "There is not enough money on your exchange balance"}
            return JsonResponse(error_message, status=400)

        # Available positions and orders checking
        result = check_pos_and_orders(request)
        result_data = json.loads(result.content.decode('utf-8'))

        if not result_data['no_positions'] or not result_data['no_orders']:
            error_message = {"error": "You have open positions or orders for this currency"}
            return JsonResponse(error_message, status=400)

        # Available bots checking
        result = check_bots(request)
        result_data = json.loads(result.content.decode('utf-8'))

        if not result_data['no_bots']:
            error_message = {"error": "You already have a similar bot"}
            return JsonResponse(error_message, status=400)

        # 233-StartTradingButtonLogicToMobileDashboardArchive
        current_time = timezone.now()
        if restart_bot:
            trading_bot = get_object_or_404(TradingBots, id=item_id)
            trading_bot.launch_date = current_time.strftime("%Y-%m-%d %H:%M:%S")
            trading_bot.status = "created"
            trading_bot.save()
            bot_id = trading_bot.id
        else:
            trading_bot = TradingBots()
            trading_bot.user = user

            instance = OptimizedStrategies(
                json_data=activity_instance.data,
                user=custom_user,
                optimized_settings=activity_instance.data["SETTINGS"],
                strategy=strategy,
                exchange = exchange
            )
            instance.save()

            trading_bot.optimized_strategy = instance
            trading_bot.trading_pair = asset
            trading_bot.strategy_name = strategy
            trading_bot.exchange = exchange
            trading_bot.launch_date = current_time.strftime("%Y-%m-%d %H:%M:%S")
            trading_bot.status = "created"
            trading_bot.investment_amount = investment_amount
            trading_bot.leverage = leverage
            trading_bot.margin_type = "ISOLATED"
            trading_bot.save()
            bot_id = trading_bot.id

        optimized_data = get_object_or_404(OptimizedStrategies, id=trading_bot.optimized_strategy.id)
        # 233-StartTradingButtonLogicToMobileDashboardArchive

        if strategy == "expo_grid" or strategy == "preset-expo_grid":
            data = {
                "bot_id": bot_id,
                "user_id": request.user.id,
                "symbol": asset,
                "available_balance": optimized_data.json_data["INITIAL BALANCE"],
                "leverage": optimized_data.json_data['LEVERAGE'],
                "num_of_grids": optimized_data.optimized_settings["NUM OF GRIDS"],
                "timeframe": optimized_data.optimized_settings["TIMEFRAME"],
                "price_range": optimized_data.optimized_settings["PRICE RANGE"],
                "activation_trigger_in_percent": optimized_data.optimized_settings[
                    "ACTIVATION TRIGGER IN PERCENT"
                ],
                "distribution_of_grid_lines": optimized_data.optimized_settings[
                    "DISTRIBUTION OF GRID LINES"
                ],
                "line_disbalance_direction": optimized_data.optimized_settings[
                    "LINE DISBALANCE DIRECTION"
                ],
                "short_stop_loss_in_percent": optimized_data.optimized_settings[
                    "SHORT STOP LOSS IN PERCENT"
                ],
                "long_stop_loss_in_percent": optimized_data.optimized_settings[
                    "LONG STOP LOSS IN PERCENT"
                ],
                "grid_disbalance_direction": optimized_data.optimized_settings[
                    "GRID DISBALANCE DIRECTION"
                ],
                "trend_period_timeframe": optimized_data.optimized_settings[
                    "TREND PERIOD TIMEFRAME"
                ],
                "trend_period": optimized_data.optimized_settings["TREND PERIOD"],
                # "margin_type": margin_type,
            }
            response = requests.post(EXPO_GRID_START_BOT, data=data)
            if response.status_code == 200:
                print("Grid bot started!")
                trading_bot.status = "started"
                trading_bot.save()
            else:
                print(
                    f"H81:0 ?@8 70?CA:5 grid 1>B0. >4 A>AB>O=8O: {response.status_code}"
                )
            return JsonResponse({'message': 'ok'}, status=200)

        elif strategy == "jumper" or strategy == "preset-jumper":
            data = {
                "bot_id": bot_id,
                "user_id": request.user.id,
                "symbol": asset,
                "available_balance": investment_amount,
                "leverage": leverage,
                "long_entry_sum_in_dollars": optimized_data.optimized_settings[
                    "AMOUNT FOR LONG"
                ],
                "short_entry_sum_in_dollars": optimized_data.optimized_settings[
                    "AMOUNT FOR SHORT"
                ],
                "long_take_profit_percent": optimized_data.optimized_settings[
                    "LONG TP %"
                ],
                "long_stop_loss_percent": optimized_data.optimized_settings[
                    "LONG SL %"
                ],
                "short_take_profit_percent": optimized_data.optimized_settings[
                    "SHORT TP %"
                ],
                "short_stop_loss_percent": optimized_data.optimized_settings[
                    "SHORT SL %"
                ],
                "price_difference_long_entry": optimized_data.optimized_settings[
                    "LONG DIVERGENCE %"
                ],
                "price_difference_short_entry": optimized_data.optimized_settings[
                    "SHORT DIVERGENCE %"
                ],
                "block_long_trade_until": None,
                "block_short_trade_until": None,
                "long_pause_after_trade_min": optimized_data.optimized_settings[
                    "LONG PAUSE MINUTE"
                ],
                "short_pause_after_trade_min": optimized_data.optimized_settings[
                    "SHORT PAUSE MINUTE"
                ],
                "order_expiration_by_price_percent_limit": optimized_data.optimized_settings[
                    "PRICE CHANGE LIMIT %"
                ],
                "short_period": optimized_data.optimized_settings["SHORT PERIOD"],
                "long_period": optimized_data.optimized_settings["LONG PERIOD"],
                "long_trailing_stop": optimized_data.optimized_settings[
                    "LONG TRAILING STOP"
                ],
                "short_trailing_stop": optimized_data.optimized_settings[
                    "SHORT TRAILING STOP"
                ],
            }
            response = requests.post(JUMPER_START_BOT, data=data)
            if response.status_code == 200:
                print("Jumper bot started!")
                trading_bot.status = "started"
                trading_bot.save()
            else:
                print(
                    f"H81:0 ?@8 70?CA:5 jumper 1>B0. >4 A>AB>O=8O: {response.status_code}"
                )

            return JsonResponse({'message': 'ok'}, status=200)


        return redirect("main_service:backtest_and_optimization_history")
