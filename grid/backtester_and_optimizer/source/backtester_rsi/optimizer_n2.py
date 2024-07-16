import numpy as np
import pandas as pd

from datetime import datetime, timedelta

from sqlalchemy import text

from source.backtester_rsi.utils import backtest
from source.backtester_rsi.configs import BALANCE, MARGIN

from db_config import engine


def backtester_rsi(
    chosen_strategy,
    symbol,
    days_of_backtest,
    just_backtest,
    interval_for_backtest,
    start_balance=BALANCE,
):
    """Main function that executes the program."""
    global k_lines
    result = {}
    # now = datetime.now(pytz.utc)
    # today = datetime.now().date()
    # datetime_format = "%Y-%m-%d %H:%M"
    # error_message = ""

    connection = engine.connect()
    table_name_data = "futures_data_1m"
    table_name_assets = "assets"
    # end_date = datetime.now() - timedelta(days=days_of_backtest)
    end_date = datetime.now() - timedelta(days=30)
    start_time = datetime.now()
    try:
        query = text(
            f"SELECT timestamp, open, high, low, close "
            f"FROM {table_name_data} d "
            f"JOIN {table_name_assets} a ON d.asset_id = a.id "
            f"WHERE a.asset = :symbol AND d.timestamp > :end_date "
            f"ORDER BY d.timestamp DESC ;"
        ).params(symbol=symbol.upper(), end_date=end_date)

        # Execute the SQL query using the connection
        k_lines = connection.execute(query).fetchall()

    except Exception as ex:
        print(ex)
    connection.close()
    print(datetime.now() - start_time)
    historical_data = pd.DataFrame(k_lines)
    if not just_backtest:
        all_intervals = sorted(
            [
                backtest(
                    chosen_strategy=chosen_strategy,
                    symbol=symbol,
                    hist_data=historical_data,
                    strategy_interval=interval,
                    balance=start_balance,
                    money_in=MARGIN,
                )
                for interval in np.arange(0.01, 3, 0.01)
            ],
            key=lambda x: -x["PNL in %"],
        )
        # Get the best result from all intervals
        best_result = all_intervals[0]
        # Print the best result
        for k, v in best_result.items():
            if k == "interval":
                result[k] = str(v)
            else:
                result[k] = str(v)
        return result
    elif just_backtest:
        return backtest(
            chosen_strategy=chosen_strategy,
            symbol=symbol,
            hist_data=historical_data,
            strategy_interval=float(interval_for_backtest),
            balance=start_balance,
            money_in=MARGIN,
            days_of_backtest=days_of_backtest,
        )


if __name__ == "__main__":
    start_time = datetime.now()
    result = backtester_rsi("F1", "BTCUSDT", 30, False, 1.35, 1000)
    print(datetime.now() - start_time)
    print(result)
