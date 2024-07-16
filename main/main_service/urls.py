from django.template.defaulttags import url
from django.urls import path, include
from main_service.views import (
    index,
    profile,
    deposit,
    trading_description,
    redirect_to_page,
    basket,
    support,
    payment_history,
    api_keys_update,
    binance_guide,
    email_confirmation,
    dashboard,
    dashboard_edit,
    dashboard_details,
    # dashboard_start,
    ai_optimizer,
    delete_bot,
    dashboard_stop,
    add_to_dashboard,
    get_minimal_quantity,
    backtest_and_optimization_history,
    get_asset,
    get_market,
    get_exchange,
    get_strategy,
    get_default_settings,
    dashboard_stop_and_close,
    get_dashboard_info,
    mobile_dashboard,
    trading_description_bybit,
    get_bybit_expo_grid_bot_settings,
    get_bybit_open_order_rules,
    get_bybit_backtest_and_optimization_params,
    backtest_optimization_start_bot,
    delete_archive_data,
    test_view,
    privacy_policy,
    risk_disclaimer,
    password_change_view,
    get_backtest_and_optimize_jumper_params,
    get_jumper_bot_settings,
    change_api_keys,
    confirm_email
)
from crypto_service.views import (
    backtest_optimization,
    backtest,
    add_to_dashboard_without_optimize,
    crypto_optimize,
    check_user_api_keys,
    create_bot,
    check_balance,
    check_pos_and_orders,
    check_bots,
    check_ats,
    start_bot,
    optimize,
    admin_dashboard,
    check_user_api_keys_bybit,
    check_account_status,
)
from stock_service.views import stock_index
from forex_service.views import forex_index
from commodity_service.views import commodity_index
from django.contrib.auth.views import (
    # PasswordResetView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    # PasswordResetForm
)

from main_service.views import (CustomPasswordResetView, start_trading_from_archive, get_last_preset_data,
                                get_progress_data, get_last_data_id, update_optimization_data)
from django.views.decorators.cache import cache_page

from source.utils import get_assets_list

urlpatterns = [
    path("", index, name="index"),
    path("", include("stock_service.urls", namespace="stock_service")),
    path("accounts/", include("django.contrib.auth.urls")),
    path("dashboard/", cache_page(1)(dashboard), name="dashboard"),
    path("delete_bot/<int:bot_id>/", delete_bot, name="delete_bot"),
    path("stock/", stock_index, name="stock"),
    path("ai_optimizer/", ai_optimizer, name="ai_optimizer"),
    # path("optimizate/", check_user_api_keys, name="check_user_api_keys"),
    path("profile/", profile, name="profile"),
    path(
        "profile/<str:verification_code>/",
        email_confirmation,
        name="email_confirmation",
    ),
    path("deposit/", deposit, name="deposit"),
    path("payment_history/", payment_history, name="payment_history"),
    path("basket/", basket, name="basket"),
    path("support/", support, name="support"),
    path("trading_description/", trading_description, name="trading_description"),
    path(
        "trading_description_bybit/",
        trading_description_bybit,
        name="trading_description_bybit",
    ),
    path("binance_guide/", binance_guide, name="binance_guide"),
    path("forex/", forex_index, name="forex"),
    path("commodity/", commodity_index, name="commodity"),
    path(
        "dashboard_edit/<uuid:user_id>/<int:strategy_id>/",
        dashboard_edit,
        name="dashboard_edit",
    ),
    path(
        "dashboard_details/<uuid:user_id>/<int:strategy_id>/",
        dashboard_details,
        name="dashboard_details",
    ),
    # path("dashboard_start/<int:strategy_id>/", dashboard_start, name="dashboard_start"),
    path("dashboard_stop/<int:strategy_id>/", dashboard_stop, name="dashboard_stop"),
    path(
        "dashboard_stop_and_close/<int:strategy_id>/",
        dashboard_stop_and_close,
        name="dashboard_stop_and_close",
    ),
    path("redirect/<str:image_name>/", redirect_to_page, name="redirect_to_page"),
    path(
        "api_keys_update/",
        api_keys_update,
        name="api_keys_update",
    ),
    path("add_to_dashboard/", add_to_dashboard, name="add_to_dashboard"),
    path(
        "get_minimal_quantity/<str:symbol>/",
        get_minimal_quantity,
        name="get_minimal_quantity",
    ),
    # Backtest and Optimizer endpoints
    path("backtest_optimization/", backtest_optimization, name="backtest_optimization"),
    path(
        "backtest_and_optimization_history",
        backtest_and_optimization_history,
        name="backtest_and_optimization_history",
    ),
    path("get_market/<str:exchange>/", get_market, name="get_market"),
    path("get_exchange/<str:market>/", get_exchange, name="get_exchange"),
    path("get_asset/<str:exchange>/", get_asset, name="get_asset"),
    path("get_strategy/<str:exchange>/", get_strategy, name="get_strategy"),
    path(
        "get_strategy_df_settings/<str:strategy>/",
        get_default_settings,
        name="get_default_settings",
    ),
    path("backtest/", backtest, name="backtest"),
    path(
        "add_to_dashboard_without_optimize/",
        add_to_dashboard_without_optimize,
        name="add_to_dashboard_without_optimize",
    ),
    # Create ats endpoints
    path(
        "check_user_api_keys/", check_user_api_keys, name="check_user_api_keys"
    ),  # check if user exchange keys saved
    path(
        "check_user_api_keys_bybit/",
        check_user_api_keys_bybit,
        name="check_user_api_keys_bybit",
    ),  # check if user exchange keys saved
    path("optimize/", optimize, name="optimize"),
    path(
        "crypto_optimize/", crypto_optimize, name="crypto_optimize"
    ),  # optimization based on chosen data
    path(
        "check_balance/", check_balance, name="check_balance"
    ),  # Check user balance (takes strategy_id)
    path("check_pos_and_orders/", check_pos_and_orders, name="check_pos_and_orders"),

    # 163-SimilarBotChecking
    path("check_bots/", check_bots, name="check_bots"),
    # 163-SimilarBotChecking
    # 230-AccountStatusChecking
    path("check_account_status/", check_account_status, name="check_account_status"),
    # 230-AccountStatusChecking
    # 228-ATSChecking
    path("check_ats/", check_ats, name="check_ats"),
    # 228-ATSChecking
    path("create_bot/", create_bot, name="create_bot"),
    path("start_bot/<int:strategy_id>/", start_bot, name="start_bot"),
    path("admin_dashboard/", admin_dashboard, name="admin_dashboard"),
    path("get_dashboard_info/", get_dashboard_info, name="get_dashboard_info"),
    path("mobile_dashboard/", mobile_dashboard, name="mobile_dashboard"),
    # path("get_binance_assets/", get_binance_assets, name="get_binance_assets"),
    # 314-DB2Range
    path("get_assets_list/", get_assets_list, name="get_assets_list"),
    # 314-DB2Range
    path(
        "get_bybit_expo_grid_bot_settings/",
        get_bybit_expo_grid_bot_settings,
        name="get_bybit_expo_grid_bot_settings",
    ),
    path(
        "get_bybit_open_order_rules/",
        get_bybit_open_order_rules,
        name="get_bybit_open_order_rules",
    ),
    path(
        "get_bybit_backtest_and_optimization_params/",
        get_bybit_backtest_and_optimization_params,
        name="get_bybit_backtest_and_optimization_params",
    ),
    path(
        "backtest_optimization_start_bot/",
        backtest_optimization_start_bot,
        name="backtest_optimization_start_bot",
    ),
    path("delete_archive_data/", delete_archive_data, name="delete_archive_data"),
    path("test/", test_view, name="test_view"),
    path("privacy_policy/", privacy_policy, name="privacy_policy"),
    path("risk_disclaimer/", risk_disclaimer, name="risk_disclaimer"),
    path("password_change/", password_change_view, name="password_change_view"),
    path(
        "get_backtest_and_optimize_jumper_params/",
        get_backtest_and_optimize_jumper_params,
        name="get_backtest_and_optimize_jumper_params",
    ),
    path(
        "get_jumper_bot_settings/",
        get_jumper_bot_settings,
        name="get_jumper_bot_settings",
    ),
    path(
        "change_api_keys/", change_api_keys, name="change_api_keys",
    ),
    path('custom_password-reset/', CustomPasswordResetView.as_view(), name='custom_password_reset'),
    path('password-reset/done/', PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('password-reset/confirm/<uidb64>/<token>/', PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('password-reset/complete/', PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    path('start_trading_from_archive/<int:item_id>/', start_trading_from_archive, name='start_trading_from_archive'),
    # Quick start new logic update
    path("get_last_preset_data/<str:symbol>/<str:exchange>/", get_last_preset_data, name="get_last_preset_data"),
    # 58-archiveAndLaboratoryProgressbar
    path("get_progress_data/", get_progress_data, name="get_progress_data"),
    path("get_last_data_id/", get_last_data_id, name="get_last_data_id"),
    # 60-DataFromOptimizer
    path("update_optimization_data/", update_optimization_data, name="update_optimization_data"),
    path('confirm/<str:user_pk>/<str:email_hash>/<str:token>/', confirm_email, name='confirm_email'),

]
app_name = "main_service"
