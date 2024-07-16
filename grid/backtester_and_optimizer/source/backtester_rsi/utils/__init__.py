import numpy as np
import pandas as pd


def _transform_data(data: pd.DataFrame) -> np.ndarray:
    """
    Transform the close price data from a DataFrame into a NumPy array.

    Args:
        data (pd.DataFrame): DataFrame containing the close price data.

    Returns:
        NumPy array of the transformed close price data.
    """

    data_close = data.close.to_numpy().reshape(data.shape[0], 1)

    return data_close


def _calculate_result(
    result_dict: dict[str, float],
    interval: float,
    money_in: float,
    fee: float,
    days_of_backtest: int,
) -> dict[str, int | float | str]:
    """
    Calculate various result metrics based on the input parameters.

    Args:
        chosen_strategy: user chosen strategy
        symbol: Selected trading instrument
        result_dict (dict[str, float]): Dictionary containing the result values.
        interval (float): Time interval.
        money_in (float): Amount of money invested.
        fee (float): Fee percentage.
        days_of_backtest (int): Count of days for backtest from today.

    Returns:
        Dictionary with the calculated result metrics.
    """
    # Create a copy of the result_dict to avoid modifying the original one
    d = result_dict.copy()
    d["total trades"] = d["SL"] + d["TP"]
    d["margin in $"] = money_in
    d["profit ratio"] = np.round(d["TP"] / d["total trades"], 2)
    d["fees"] = np.round(d["total trades"] * money_in * fee, 3)
    d["TP in $"] = np.round(d["TP"] * interval * money_in, 3)
    d["SL in $"] = np.round(d["SL"] * interval * money_in, 3)
    # Todo do
    # d['drawdown']
    d["end balance"] = np.round(
        d["start balance"] + d["TP in $"] - d["SL in $"] - d["fees"], 3
    )
    d["PNL in $"] = np.round(d["end balance"] - d["start balance"], 3)
    d["PNL in %"] = np.round((d["end balance"] / d["start balance"] - 1) * 100, 2)
    d["APY in %"] = np.round(365 / days_of_backtest * d["PNL in %"], 2)

    return d


def _get_tp_sl(
    x: float,
    interval: float,
    trend: str = "up",
) -> tuple[float, float]:
    """
    Calculate the take profit (TP) and stop loss (SL) values
    based on the input parameters.

    Args:
        x (float): The initial value.
        interval (float): The interval to calculate TP and SL.
        trend (str, optional): The trend direction.

    Returns:
        The TP and SL values.
    """

    tp = x + x * interval
    sl = x - x * interval
    # Swap TP and SL values if the trend is 'down'
    if trend == "down":
        tp, sl = sl, tp

    return tp, sl


def backtest(
    chosen_strategy: str,
    symbol: str,
    hist_data: pd.DataFrame,
    strategy_interval: float,
    balance: float = 1000.0,
    money_in: float = 260.0,
    fee: float = 0.021,
    days_of_backtest: int = 30,
) -> dict[str, int | float | str]:
    """
    Perform a backtest of a trading strategy based on historical data.

    Args:
        chosen_strategy: user chosen strategy
        symbol: Selected trading instrument
        hist_data (pd.DataFrame): Historical data for the asset.
        strategy_interval (float): The interval value for the trading strategy.
        balance (float): Initial balance. Defaults to 100.
        money_in (float): Amount of money invested. Defaults to 26.
        fee (float): Fee percentage. Defaults to 0.012 + 0.03.
        days_of_backtest (int): Count of days for backtest from today.

    Returns:
        dict: Dictionary with the backtest results.
    """

    trades = {
        # 'symbol': hist_data.index[0][0],
        "interval": np.round(strategy_interval, 3),
        "chosen_strategy": chosen_strategy,
        "start balance": balance,
        "TP": 0,
        "SL": 0,
    }
    # Transform the historical data into a NumPy array
    quotes_data = _transform_data(hist_data)

    trend = "up"
    strategy_interval /= 100
    fee /= 100

    # Calculate the initial TP and SL values
    move_up, move_down = _get_tp_sl(
        x=quotes_data[0],
        interval=strategy_interval,
    )
    # Create a new array with shifted quotes data for comparison
    quotes_data = np.hstack((quotes_data[:-1], quotes_data[1:]))
    # Find the index where the trend changes
    start_i = 0

    for i, (prev, current) in enumerate(quotes_data):
        start_i = i
        if prev < move_up < current:
            trend = "up"
            break
        elif prev > move_down > current:
            trend = "down"
            break
    # Remove the irrelevant quotes data before the trend change
    quotes_data = quotes_data[start_i + 1 :]

    take_profit, stop_loss = _get_tp_sl(
        x=quotes_data[0, 1],
        interval=strategy_interval,
        trend=trend,
    )

    for prev, current in quotes_data:
        if trend == "up":
            if prev < take_profit < current:
                trades["TP"] = trades.get("TP") + 1
                take_profit, stop_loss = _get_tp_sl(
                    take_profit, interval=strategy_interval
                )

            elif prev > stop_loss > current:
                trend = "down"
                trades["SL"] = trades.get("SL") + 1
                take_profit, stop_loss = _get_tp_sl(
                    stop_loss, interval=strategy_interval, trend=trend
                )
        elif trend == "down":
            if prev > take_profit > current:
                trades["TP"] = trades.get("TP") + 1
                take_profit, stop_loss = _get_tp_sl(
                    take_profit, interval=strategy_interval, trend=trend
                )
            elif prev < stop_loss < current:
                trend = "up"
                trades["SL"] = trades.get("SL") + 1
                take_profit, stop_loss = _get_tp_sl(
                    stop_loss, interval=strategy_interval
                )

    trades["current trend"] = trend
    trades["symbol"] = symbol

    # Calculate the result metrics based on the trades dictionary
    result = _calculate_result(
        result_dict=trades,
        interval=strategy_interval,
        money_in=money_in,
        fee=fee,
        days_of_backtest=days_of_backtest,
    )

    return result
