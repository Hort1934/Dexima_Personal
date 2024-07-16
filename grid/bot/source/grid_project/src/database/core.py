import datetime

import pandas as pd
from sqlalchemy import text

from source.grid_project.src.config.settings import load_settings


_EXCHANGES = ("bybit", "binance")

settings = load_settings()
from db_config import engine


# engine = create_engine(
#     f"postgresql://{settings.db.user}:{settings.db.password}@{settings.db.host}:{settings.db.port}/{settings.db.db}"
# )
connection = engine.connect()


class Database:
    def __init__(self, conn):
        self._conn = conn
        self.table_name_assets = "assets"
        self.timeframe_unit = "minutes"
        self.df = pd.DataFrame

    def get_historical_data(
        self,
        exchange: str,
        type_: str,
        symbol: str,
        timeframe: str,
        from_: datetime.datetime,
        to: datetime.datetime,
    ):
        from_str = from_.strftime("%Y-%m-%d")
        to_str = to.strftime("%Y-%m-%d")

        # if exchange wrong return smth
        # 1s,1m 5m, 15,1h
        if exchange not in _EXCHANGES:
            return
        if timeframe.endswith("m"):
            tablename = f"{exchange.lower()}_{type_.lower()}_data_1m"
        elif timeframe.endswith("s"):
            tablename = f"{exchange.lower()}_{type_.lower()}_data_1s"
            self.timeframe_unit = "seconds"
        elif timeframe.endswith("h"):
            tablename = f"{exchange.lower()}_{type_.lower()}_data_1h"
            self.timeframe_unit = "hours"
        elif timeframe.endswith("d"):
            tablename = f"{exchange.lower()}_{type_.lower()}_data_1h"
            self.timeframe_unit = "days"
        else:
            return

        interval = int(timeframe[:-1])

        try:
            query = text(
                "SELECT timestamp, open, high, low, close "
                f"FROM {tablename} d "
                f"JOIN {self.table_name_assets} a ON d.asset_id = a.id "
                "WHERE a.asset = :symbol "
                "AND d.timestamp > TO_TIMESTAMP(:start_date, 'YYYY-MM-DD') "
                "AND d.timestamp < TO_TIMESTAMP(:end_date, 'YYYY-MM-DD') "
                "ORDER BY d.timestamp DESC ;"
            ).params(symbol=symbol.upper(), start_date=from_str, end_date=to_str)

            k_lines = self._conn.execute(query).fetchall()
            self.df = pd.DataFrame(k_lines)
        except Exception as ex:
            print(ex)

        # self._conn.close()
        return self.aggregate_custom_timeframe(self.df, interval, self.timeframe_unit)

        # examople usage minute_df = aggregate_custom_timeframe(df, 5, 'minutes')

    def aggregate_custom_timeframe(self, df, timeframe, timeframe_unit):
        # Преобразование 'date' в формат даты/времени (если не уже в таком формате)
        df["date"] = pd.to_datetime(df["timestamp"])

        if timeframe_unit == "minutes":
            index = (
                (df["date"] - pd.Timestamp(0))
                .floordiv(pd.Timedelta(minutes=timeframe))
                .astype(int)
            )
            return self.aggregator(index, df, timeframe, timeframe_unit)
        elif timeframe_unit == "hours":
            index = (
                (df["date"] - pd.Timestamp(0))
                .floordiv(pd.Timedelta(hours=timeframe))
                .astype(int)
            )
            return self.aggregator(index, df, timeframe, timeframe_unit)
        elif timeframe_unit == "seconds":
            index = (
                (df["date"] - pd.Timestamp(0))
                .floordiv(pd.Timedelta(seconds=timeframe))
                .astype(int)
            )
            return self.aggregator(index, df, timeframe, timeframe_unit)
        elif timeframe_unit == "days":
            index = (
                (df["date"] - pd.Timestamp(0))
                .floordiv(pd.Timedelta(days=timeframe))
                .astype(int)
            )
            return self.aggregator(index, df, timeframe, timeframe_unit)

        else:
            raise ValueError(
                "Invalid 'timeframe_unit'. Use 'minutes', 'hours', or 'seconds'."
            )

    @staticmethod
    def aggregator(index, df, timeframe, timeframe_unit):
        df["date"] = pd.to_datetime(df["date"])

        # Группировка данных по пользовательскому временному интервалу
        grouped = df.groupby(index)

        # Вычисление 'open', 'high', 'low', 'close'
        ohlc_df = grouped.agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}
        )

        # Преобразование индекса обратно в datetime
        if timeframe_unit == "minutes":
            ohlc_df["date"] = pd.to_datetime(
                ohlc_df.index * pd.Timedelta(minutes=timeframe) + pd.Timestamp(0)
            )
        elif timeframe_unit == "hours":
            ohlc_df["date"] = pd.to_datetime(
                ohlc_df.index * pd.Timedelta(hours=timeframe) + pd.Timestamp(0)
            )
        elif timeframe_unit == "days":
            ohlc_df["date"] = pd.to_datetime(
                ohlc_df.index * pd.Timedelta(days=timeframe) + pd.Timestamp(0)
            )
        elif timeframe_unit == "seconds":
            ohlc_df["date"] = pd.to_datetime(
                ohlc_df.index * pd.Timedelta(seconds=timeframe) + pd.Timestamp(0)
            )
        return ohlc_df


if __name__ == "__main__":
    connection = engine.connect()
    db = Database(connection)
    from_ = "2024-01-18"
    to = "2024-01-26"

    print(
        db.get_historical_data(
            exchange="bybit",
            type_="futures",
            symbol="BTCUSDT",
            timeframe="4d",
            from_=from_,
            to=to,
        )
    )
