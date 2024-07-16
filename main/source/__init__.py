import datetime
import hashlib
import hmac
import time
import requests
import json
from datetime import timedelta
from main_service.models import UserStatus, Statuses


def send_signed_bybit_default_request(method, endpoint, api_key, api_secret, payload=None):
    url = "https://api.bybit.com"

    time_stamp = str(int(time.time() * 10 ** 3))
    param_str = str(time_stamp) + api_key + '5000' + payload
    hash = hmac.new(bytes(api_secret, "utf-8"), param_str.encode("utf-8"), hashlib.sha256)
    signature = hash.hexdigest()

    headers = {
        'X-BAPI-API-KEY': api_key,
        'X-BAPI-SIGN': signature,
        'X-BAPI-SIGN-TYPE': '2',
        'X-BAPI-TIMESTAMP': time_stamp,
        'X-BAPI-RECV-WINDOW': '5000',
        'Content-Type': 'application/json'
    }

    response = requests.request(method, f'{url}{endpoint}?{payload}', headers=headers)

    return response.json()


def send_signed_default_request(method, endpoint, api_key, api_secret, params=None):
    base_url = "https://fapi.binance.com"
    timestamp = int(time.time() * 1000)

    if params is None:
        params = {}

    params["timestamp"] = timestamp
    query_string = "&".join([f"{key}={params[key]}" for key in params])
    signature = hmac.new(
        api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
    ).hexdigest()

    headers = {
        "X-MBX-APIKEY": api_key,
    }

    if method == "GET":
        full_url = f"{base_url}{endpoint}?{query_string}&signature={signature}"
        response = requests.get(full_url, headers=headers)
    else:
        # Handle other HTTP methods if needed
        raise ValueError("Unsupported HTTP method")

    return response.json()


def auto_setting_of_trial_status(user):
    user_id = user.id
    username = user.username
    if username == "maxitoska" or username == "SlavaLapin":
        current_date = datetime.datetime.now()

        user_status = UserStatus()
        statuses = Statuses.objects.all()[3]
        user_status.user_id = user_id
        user_status.status_id = statuses.id
        user_status.max_investment = statuses.max_investment
        user_status.max_ats_count = statuses.max_ats_count
        user_status.max_backtests = statuses.max_backtests
        user_status.max_optimizations = statuses.max_optimizations
        user_status.backtest_and_optimization_duration_days = (
            statuses.backtest_and_optimization_duration_days
        )
        user_status.expiration_date = current_date + timedelta(days=30)
        user_status.save()
    else:
        current_date = datetime.datetime.now()

        user_status = UserStatus()
        statuses = Statuses.objects.all()[0]
        user_status.user_id = user_id
        user_status.status_id = statuses.id
        user_status.max_investment = statuses.max_investment
        user_status.max_ats_count = statuses.max_ats_count
        user_status.max_backtests = statuses.max_backtests
        user_status.max_optimizations = statuses.max_optimizations
        user_status.backtest_and_optimization_duration_days = (
            statuses.backtest_and_optimization_duration_days
        )
        user_status.expiration_date = current_date + timedelta(days=30)
        user_status.save()
    user.num_of_optimization = user_status.max_optimizations
    user.num_of_backtesting = user_status.max_optimizations
    user.num_of_ats = user_status.max_ats_count
    user.save()
