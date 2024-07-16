import datetime

from db_config import engine
from source.grid_project.src.common.strategy import ExpoGridStrategy
from source.grid_project.src.common.strategy.expo_grid.grid import Grid
from source.grid_project.src.common.strategy.expo_grid.settings import (
    ExpoGridStrategySettings,
)
from source.grid_project.src.database.core import Database, connection
from source.grid_project.src.services.executor import BacktestExecutor
from source.grid_project.src.services.optimizer.optimizer import Optimizer, save_results


async def start_grid_bot_optimize(
    symbol, leverage, available_balance, from_, to, params, backtest_and_optimization_id
):
    settings = ExpoGridStrategySettings.from_file()

    if params["num_of_grids"]["checked"]:
        list_ = params["num_of_grids"]
        num_of_grids = [
            i
            for i in range(
                int(list_["num_of_grids_start"]),
                int(list_["num_of_grids_end"]) + int(list_["num_of_grids_step"]),
                int(list_["num_of_grids_step"]),
            )
        ]
    else:
        num_of_grids = [int(params["num_of_grids"]["value"])]
    if params["timeframe"]["checked"]:
        timeframe_list = params["timeframe"]["timeframe_list"]
        list_ = params["timeframe"]
        timeframe = filter_timeframes(
            timeframe_list, list_["timeframe_start"], list_["timeframe_end"]
        )
    else:
        timeframe = [params["timeframe"]["value"]]
    if params["price_range"]["checked"]:
        list_ = params["price_range"]
        price_range = [
            i
            for i in range(
                int(list_["price_range_start"]),
                int(list_["price_range_end"]) + int(list_["price_range_step"]),
                int(list_["price_range_step"]),
            )
        ]
    else:
        price_range = [int(params["price_range"]["value"])]
    if params["activation_trigger_in_percent"]["checked"]:
        list_ = params["activation_trigger_in_percent"]
        activation_trigger_in_percent_start = float(
            list_["activation_trigger_in_percent_start"]
        )
        activation_trigger_in_percent_end = float(
            list_["activation_trigger_in_percent_end"]
        )
        activation_trigger_in_percent_step = float(
            list_["activation_trigger_in_percent_step"]
        )

        # Generate the list using a loop
        activation_trigger_in_percent = []
        current_value = activation_trigger_in_percent_start
        while current_value <= activation_trigger_in_percent_end:
            activation_trigger_in_percent.append(current_value)
            current_value += activation_trigger_in_percent_step
    else:
        activation_trigger_in_percent = [
            float(params["activation_trigger_in_percent"]["value"])
        ]

    if params["distribution_of_grid_lines"]["checked"]:
        list_ = params["distribution_of_grid_lines"]
        if (
            list_["distribution_of_grid_lines_start"]
            != list_["distribution_of_grid_lines_end"]
        ):
            distribution_of_grid_lines = [
                [
                    list_["distribution_of_grid_lines_start"],
                    list_["distribution_of_grid_lines_end"],
                ]
            ]
        else:
            distribution_of_grid_lines = [list_["distribution_of_grid_lines_start"]]
    else:
        distribution_of_grid_lines = [params["distribution_of_grid_lines"]["value"]]

    if params["short_stop_loss_in_percent"]["checked"]:
        list_ = params["short_stop_loss_in_percent"]
        short_stop_loss_in_percent_start = float(
            list_["short_stop_loss_in_percent_start"]
        )
        short_stop_loss_in_percent_end = float(list_["short_stop_loss_in_percent_end"])
        short_stop_loss_in_percent_step = float(
            list_["short_stop_loss_in_percent_step"]
        )
        short_stop_loss_in_percent = []
        current_value = short_stop_loss_in_percent_start
        while current_value <= short_stop_loss_in_percent_end:
            short_stop_loss_in_percent.append(current_value)
            current_value += short_stop_loss_in_percent_step
        if not short_stop_loss_in_percent:
            short_stop_loss_in_percent.append(current_value)
    else:
        short_stop_loss_in_percent = [
            float(params["short_stop_loss_in_percent"]["value"])
        ]
    if params["long_stop_loss_in_percent"]["checked"]:
        list_ = params["long_stop_loss_in_percent"]
        long_stop_loss_in_percent_start = float(
            list_["long_stop_loss_in_percent_start"]
        )

        long_stop_loss_in_percent_end = float(list_["long_stop_loss_in_percent_end"])
        long_stop_loss_in_percent_step = float(list_["long_stop_loss_in_percent_step"])

        # Generate the list using a loop
        long_stop_loss_in_percent = []
        current_value = long_stop_loss_in_percent_start
        while current_value <= long_stop_loss_in_percent_end:
            long_stop_loss_in_percent.append(current_value)
            current_value += long_stop_loss_in_percent_step
        if not long_stop_loss_in_percent:
            long_stop_loss_in_percent.append(current_value)
    else:
        long_stop_loss_in_percent = [
            float(params["long_stop_loss_in_percent"]["value"])
        ]
    if params["trend_period"]["checked"]:
        list_ = params["trend_period"]
        trend_period = [
            i
            for i in range(
                int(list_["trend_period_start"]),
                int(list_["trend_period_end"]) + int(list_["trend_period_step"]),
                int(list_["trend_period_step"]),
            )
        ]
    else:
        trend_period = [int(params["trend_period"]["value"])]

    grid_disbalance_direction = ["DESCENDING"]
    line_disbalance_direction = ["DESCENDING"]
    trend_period_timeframe = timeframe

    settings.optimization = {
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
    settings.symbol = symbol
    settings.leverage = int(leverage)
    settings.available_balance = float(available_balance)

    o = Optimizer(settings=settings)

    original_from_obj = datetime.datetime.strptime(from_, "%d-%m-%Y")
    from_ = original_from_obj.strftime("%Y-%m-%d")
    original_to_obj = datetime.datetime.strptime(to, "%d-%m-%Y")
    to = original_to_obj.strftime("%Y-%m-%d")

    await o.run_optimization(
        from_=datetime.datetime.strptime(from_, "%Y-%m-%d"),
        to=datetime.datetime.strptime(to, "%Y-%m-%d"),
        # 60-DataFromOptimizer
        backtest_and_optimization_id=backtest_and_optimization_id,
        # 60-DataFromOptimizer
        iterations=1000000,
    )

    print(o.get_best_result_by_param("Profit"))
    save_results(o.results)
    return o.get_best_result_by_param("Profit")


async def start_grid_bot_backtest(instance, from_, to):
    try:
        # strategy_settings = ExpoGridStrategySettings.from_file()
        db = Database(connection)

        original_from_obj = datetime.datetime.strptime(from_, "%d-%m-%Y")
        from_ = original_from_obj.strftime("%Y-%m-%d")
        original_to_obj = datetime.datetime.strptime(to, "%d-%m-%Y")
        to = original_to_obj.strftime("%Y-%m-%d")

        historical_data = (
            db.get_historical_data(
                exchange="bybit",
                type_="futures",
                symbol=instance.symbol,
                timeframe=instance.timeframe,
                # from_=datetime.datetime(2023, 10, 1),
                # to=datetime.datetime(2023, 11, 1),
                from_=datetime.datetime.strptime(from_, "%Y-%m-%d"),
                to=datetime.datetime.strptime(to, "%Y-%m-%d"),
            ).reset_index()
            # .drop(columns=["date"])
        )
        print(historical_data)
        if historical_data.empty:
            return

        executor = BacktestExecutor(
            data=historical_data, initial_balance=instance.available_balance
        )
        # logger.info(
        #     f"Connected to {executor.__class__.__name__.replace('Executor', '')}"
        # )
        async with executor:
            strategy = ExpoGridStrategy(
                executor=executor, grid=Grid(), settings=instance
            )
            while executor.is_running:
                await strategy.execute()  # noqa: ERA001, RUF100
        print(executor.position)
        print(executor.result())

        return executor.result()
    except Exception as exc:
        return exc


def filter_timeframes(timeframes, start, stop):
    # Map timeframes to their corresponding minutes
    timeframe_minutes = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "2h": 120,
        "4h": 240,
        "1d": 1440,
    }

    # Convert start and stop to minutes
    start_minutes = timeframe_minutes[start]
    stop_minutes = timeframe_minutes[stop]

    # Filter timeframes within the range
    filtered_timeframes = []
    for timeframe in timeframes:
        if (
            timeframe_minutes[timeframe] >= start_minutes
            and timeframe_minutes[timeframe] <= stop_minutes
        ):
            filtered_timeframes.append(timeframe)

    return filtered_timeframes


def process_dict(d):
    new_dict = {}
    for key, value in d.items():
        # Преобразование ключа
        new_key = key.upper().replace("_", " ")

        if isinstance(value, float):
            # Округление значений float
            new_dict[new_key] = round(value, 2)
        elif isinstance(value, dict):
            # Рекурсивная обработка вложенных словарей
            new_dict[new_key] = process_dict(value)
        else:
            new_dict[new_key] = value
    return new_dict


if __name__ == "__main__":
    connection = engine.connect()
    db = Database(connection)
    from_ = "2024-01-18"
    to = "2024-01-26"

    # print(db.get_historical_data(
    #     exchange="bybit",
    #     type_="futures",
    #     symbol="ETHUSDT",
    #     timeframe="4d",
    #     from_=from_,
    #     to=to
    # ))
