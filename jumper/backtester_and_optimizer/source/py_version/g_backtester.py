import datetime

from source.py_version.db import Database, engine


class Backter:
    def __init__(self, data, fields, available_balance) -> None:
        self.fields = fields
        self.buy_volume = 0
        self.sell_volume = 0
        self.start_capital = available_balance
        self.data = data
        self.condition_long = False
        self.condition_short = False
        self.trades = []

    def run(self):
        long_period = int(self.fields.long_period)
        short_period = int(self.fields.short_period)
        max_period = int(max([long_period, short_period]))

        for index, row in self.data.iloc[max_period:].iterrows():
            prev_candle_long = self.data.loc[index - long_period]
            prev_candle_short = self.data.loc[index - short_period]
            curr_candle = row

            self.closed_conditions(curr_candle)

            self.condition_long = self.get_condition_long(
                current_candle=curr_candle, prev_candle=prev_candle_long
            )
            self.condition_short = self.get_condition_short(
                current_candle=curr_candle, prev_candle=prev_candle_short
            )
            if (
                self.condition_long
                and (self.fields.long_entry_sum_in_dollars / self.fields.LEVERAGE)
                > self.start_capital
            ):
                break
            if (
                self.condition_short
                and (self.fields.short_entry_sum_in_dollars / self.fields.LEVERAGE)
                > self.start_capital
            ):
                break

            self.express_long_condition(current_candle=curr_candle)

            self.express_short_condition(current_candle=curr_candle)

        return self.trades

    def get_condition_long(self, current_candle, prev_candle):

        percent_difference = self.calculate_percent_rising_price(
            prev_candle["open"], current_candle["open"]
        )
        if (
            percent_difference < self.fields.price_difference_long_entry
            or prev_candle["open"] == 0
            or current_candle["open"] < prev_candle["open"]
        ):
            return False
        return True

    def get_condition_short(self, current_candle, prev_candle):

        percent_difference = self.calculate_percent_rising_price(
            prev_candle["open"], current_candle["open"]
        )
        if (
            percent_difference < self.fields.price_difference_short_entry
            or prev_candle["open"] == 0
            or current_candle["open"] > prev_candle["open"]
        ):
            return False
        return True

    def calculate_percent_rising_price(self, prev_close, curr_close):
        return abs((curr_close - prev_close) / prev_close) * 100

    def express_long_condition(self, current_candle):

        long_volume_condition = self.buy_volume == 0
        long_check_time_pause_after_trade = self.check_time_pause_after_trade(
            current_candle, self.fields.block_long_trade_until
        )

        if (
            long_volume_condition
            and self.condition_long
            and long_check_time_pause_after_trade
        ):
            self.place_order("buy", current_candle)

            self.fields.block_long_trade_until = current_candle[
                "timestamp"
            ].to_pydatetime()
            +datetime.timedelta(minutes=self.fields.long_pause_after_trade_min)
            self.condition_long = False

    def express_short_condition(self, current_candle):

        short_volume_condition = self.sell_volume == 0
        short_check_time_pause_after_trade = self.check_time_pause_after_trade(
            current_candle, self.fields.block_short_trade_until
        )

        if (
            short_volume_condition
            and self.condition_short
            and short_check_time_pause_after_trade
        ):
            self.place_order("sell", current_candle)

            self.fields.block_short_trade_until = current_candle[
                "timestamp"
            ].to_pydatetime()
            +datetime.timedelta(minutes=self.fields.short_pause_after_trade_min)
            self.condition_short = False

    def place_order(self, order_type, current_candle) -> bool:

        curr_price = current_candle["open"]
        take_profit_percent = (
            self.fields.long_take_profit_percent
            if order_type == "buy"
            else self.fields.short_take_profit_percent
        )
        stop_loss_percent = (
            self.fields.long_stop_loss_percent
            if order_type == "buy"
            else self.fields.short_stop_loss_percent
        )

        order_params = {
            "opened_price": current_candle["open"],
            "status": "opened",
            "type": "market",
            "side": order_type,
            "amount": self.get_contract_size_volume(order_type, current_candle),
            "params": {},
        }
        if order_type == "buy":
            order_params["params"]["takeProfit"] = curr_price + (
                curr_price * (take_profit_percent / 100)
            )
            order_params["params"]["stopLoss"] = curr_price - (
                curr_price * (stop_loss_percent / 100)
            )
            self.buy_volume = order_params["amount"]

        else:
            order_params["params"]["takeProfit"] = curr_price - (
                curr_price * (take_profit_percent / 100)
            )
            order_params["params"]["stopLoss"] = curr_price + (
                curr_price * (stop_loss_percent / 100)
            )
            self.sell_volume = order_params["amount"]

        self.trades.append(order_params)

    def check_time_pause_after_trade(self, current_candle, block_trade_until):
        if not block_trade_until:
            return True
        if current_candle["timestamp"].to_pydatetime() > block_trade_until:
            return True
        return False

    def get_contract_size_volume(self, order_type, current_candle):
        curr_price = current_candle["open"]

        entry_sum_in_dollars = (
            self.fields.long_entry_sum_in_dollars
            if order_type == "buy"
            else self.fields.short_entry_sum_in_dollars
        )
        return round((entry_sum_in_dollars / (curr_price) * self.fields.LEVERAGE), 2)

    def closed_conditions(self, candle):
        for trade in self.trades:
            self.trailing(trade, candle)
            self.close_by_tp_sl(trade, candle)
            self.close_expired_orders_by_price_percent(trade, candle)

    def close_expired_orders_by_price_percent(self, trade, candle):
        if trade["status"] == "opened":

            price_diff = self.calculate_percent_rising_price(
                trade["opened_price"], candle["open"]
            )
            if price_diff > self.fields.order_expiration_by_price_percent_limit:
                trade["status"] = "closed"
                trade["closed_price"] = candle["open"]
                trade["pnl"] = self.calculate_pnl(trade)
                # print(trade["pnl"])

                self.start_capital += trade["pnl"]
                setattr(self, f"{trade['side']}_volume", 0)

    def trailing(self, trade, candle):
        if trade["status"] != "opened":
            return
        current_price = candle["open"]
        entry_price = trade["opened_price"]
        if trade["side"] == "buy":
            if current_price - entry_price > current_price * (
                self.fields.long_trailing_stop / 100
            ):
                if trade["params"]["stopLoss"] < current_price - current_price * (
                    self.fields.long_trailing_stop / 100
                ):
                    trade["params"]["stopLoss"] = current_price - current_price * (
                        self.fields.long_trailing_stop / 100
                    )
        elif trade["side"] == "sell":
            if entry_price - current_price > current_price * (
                self.fields.short_trailing_stop / 100
            ):
                if trade["params"]["stopLoss"] > current_price + current_price * (
                    self.fields.short_trailing_stop / 100
                ):
                    trade["params"]["stopLoss"] = current_price + current_price * (
                        self.fields.short_trailing_stop / 100
                    )

    def close_by_tp_sl(self, trade, candle):
        if trade["status"] != "opened":
            return
        current_price = candle["open"]
        trade_stop_loss = trade["params"]["stopLoss"]
        trade_take_profit = trade["params"]["takeProfit"]

        if trade["side"] == "buy":
            if current_price > trade_take_profit or current_price < trade_stop_loss:
                trade["status"] = "closed"
                trade["closed_price"] = current_price
                trade["pnl"] = self.calculate_pnl(trade)
                # print(trade["pnl"])
                self.start_capital += trade["pnl"]

                setattr(self, f"{trade['side']}_volume", 0)

        elif trade["side"] == "sell":
            if current_price < trade_take_profit or current_price > trade_stop_loss:
                trade["status"] = "closed"
                trade["closed_price"] = current_price
                trade["pnl"] = self.calculate_pnl(trade)
                # print(trade["pnl"])
                self.start_capital += trade["pnl"]

                setattr(self, f"{trade['side']}_volume", 0)

    def calculate_pnl(self, trade):
        if trade["side"] == "buy":
            return (trade["closed_price"] - trade["opened_price"]) * trade["amount"]
        if trade["side"] == "sell":
            return (trade["opened_price"] - trade["closed_price"]) * trade["amount"]


if __name__ == "__main__":
    from g_optimizator import Fields

    connection = engine.connect()
    fields = Fields()
    # data = Database().get_historical_data(
    #     exchange="bybit",
    #     type_="futures",
    #     symbol=fields.symbol,
    #     timeframe="1s",
    #     from_="hz ot kuda brat",
    #     to="toze hz",
    # )
    symbol = "BTCUSDT"
    timeframe = "5s"
    from_ = "2023-11-03"
    to = "2023-11-10"
    db = Database(conn=connection)
    data = db.get_historical_data(
        exchange="bybit",
        type_="futures",
        symbol=symbol,
        timeframe=timeframe,
        from_=from_,
        to=to,
    )
    # data = get_data(from_str="2023-11-03", to_str="2023-11-10")
    # data = get_data(symbol, timeframe, from_, to)
    # data = data[::-1]
    # data.index = data.reset_index().index

    b = Backter(data=data, fields=fields)
    trades = b.run()
    # print(trades)
    # print(b.start_capital)
