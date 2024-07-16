import os
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy import text

load_dotenv()

POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

_EXCHANGES = ("bybit", "binance")

engine = create_engine(
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)


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
        from_: str,
        to: str,
    ):
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
                f"SELECT timestamp, open, high, low, close "
                f"FROM {tablename} d "
                f"JOIN {self.table_name_assets} a ON d.asset_id = a.id "
                f"WHERE a.asset = :symbol "
                f"AND d.timestamp > TO_TIMESTAMP(:start_date, 'YYYY-MM-DD') "
                f"AND d.timestamp < TO_TIMESTAMP(:end_date, 'YYYY-MM-DD') "
                f"ORDER BY d.timestamp ASC;"
            ).params(symbol=symbol.upper(), start_date=from_, end_date=to)

            k_lines = self._conn.execute(query).fetchall()
            self.df = pd.DataFrame(k_lines)
            if interval == 1:
                return self.df
        except Exception as ex:
            print(ex)

        return self.aggregate_custom_timeframe(self.df, interval, self.timeframe_unit)

        # examople usage minute_df = aggregate_custom_timeframe(df, 5, 'minutes')

    def aggregate_custom_timeframe(self, df, timeframe, timeframe_unit):
        if timeframe == 1:
            return self.df
        # Преобразование 'date' в формат даты/времени (если не уже в таком формате)
        # df['date'] = pd.to_datetime(df['timestamp'])

        if timeframe_unit == "minutes":
            index = (
                (df["timestamp"] - pd.Timestamp(0))
                .floordiv(pd.Timedelta(minutes=timeframe))
                .astype(int)
            )
            return self.aggregator(index, df, timeframe, timeframe_unit)
        elif timeframe_unit == "hours":
            index = (
                (df["timestamp"] - pd.Timestamp(0))
                .floordiv(pd.Timedelta(hours=timeframe))
                .astype(int)
            )
            return self.aggregator(index, df, timeframe, timeframe_unit)
        elif timeframe_unit == "seconds":
            index = (
                (df["timestamp"] - pd.Timestamp(0))
                .floordiv(pd.Timedelta(seconds=timeframe))
                .astype(int)
            )
            return self.aggregator(index, df, timeframe, timeframe_unit)
        elif timeframe_unit == "days":
            index = (
                (df["timestamp"] - pd.Timestamp(0))
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
        # Группировка данных по пользовательскому временному интервалу
        grouped = df.groupby(index)

        # Вычисление 'open', 'high', 'low', 'close'
        ohlc_df = grouped.agg(
            {"open": "first", "high": "max", "low": "min", "close": "last"}
        )

        # Преобразование индекса обратно в datetime
        if timeframe_unit == "minutes":
            ohlc_df["timestamp"] = pd.to_datetime(
                ohlc_df.index * pd.Timedelta(minutes=timeframe) + pd.Timestamp(0)
            )
        elif timeframe_unit == "hours":
            ohlc_df["timestamp"] = pd.to_datetime(
                ohlc_df.index * pd.Timedelta(hours=timeframe) + pd.Timestamp(0)
            )
        elif timeframe_unit == "days":
            ohlc_df["timestamp"] = pd.to_datetime(
                ohlc_df.index * pd.Timedelta(days=timeframe) + pd.Timestamp(0)
            )
        elif timeframe_unit == "seconds":
            ohlc_df["timestamp"] = pd.to_datetime(
                ohlc_df.index * pd.Timedelta(seconds=timeframe) + pd.Timestamp(0)
            )
        return ohlc_df
