import datetime
import time
from bybit import BybitModified


# bybit = BybitModified(
#     {
#         "apiKey": "bQF6qZZleCndQjCGMT",
#         "secret": "EMJRWJrf9zpGEYN23uZr6aiOLFlIYOcFXgw1",
#     }
# )


class Bot:
    def __init__(
        self,
        fields,
        apiKey="bQF6qZZleCndQjCGMT",
        secret="EMJRWJrf9zpGEYN23uZr6aiOLFlIYOcFXgw1",
        symbol="BTCUSDT",
        test_mode=True,
    ) -> None:
        self.bybit = BybitModified({"apiKey": apiKey, "secret": secret})

        self.bybit.set_sandbox_mode(test_mode)
        self.fields = fields
        self.symbol = symbol

    def close_expired_orders_by_price_percent(self):
        for order in self.bybit.fetch_open_orders():
            open_order_price = float(order["price"])
            order_type = order["type"]
            symbol_info = self.bybit.fetch_ticker(order["symbol"])
            if not symbol_info["visible"]:
                continue
            bid_or_ask = (
                float(symbol_info["ask"])
                if order_type == "limit"
                else float(symbol_info["bid"])
            )
            price_diff = self.calculate_percent_rising_price(
                open_order_price, bid_or_ask
            )
            if price_diff > self.fields.order_expiration_by_price_percent_limit:
                self.bybit.cancel_order(order["id"], order["symbol"])

    def on_tick(self):
        # global long_condition_for_1m, short_condition_for_1m
        self.close_expired_orders_by_price_percent()
        self.trailing()
        self.immidiate_trailing()

        long_condition_for_1m = self.is_long_percent_to_entry_reached()
        short_condition_for_1m = self.is_short_percent_to_entry_reached()

        self.express_long_condition("1m", long_condition_for_1m)
        self.express_short_condition("1m", short_condition_for_1m)

    def express_long_condition(self, timeframe, long_condition_period):
        # global block_long_trade_until
        long_orders_volume_condition = self.get_orders_volume("buy") == 0
        long_positions_volume_condition = self.get_positions_volume("buy") == 0
        long_check_time_pause_after_trade = self.check_time_pause_after_trade(
            self.fields.block_long_trade_until
        )

        if (
            long_orders_volume_condition
            and long_positions_volume_condition
            and long_condition_period
            and long_check_time_pause_after_trade
        ):
            order_sent = self.place_order("buy", timeframe)
            if order_sent:
                self.fields.block_long_trade_until = (
                    datetime.datetime.now()
                    + datetime.timedelta(minutes=self.fields.long_pause_after_trade_min)
                )
                long_condition_period = False

    def express_short_condition(self, timeframe, short_condition_period):
        # global block_short_trade_until
        short_orders_volume_condition = self.get_orders_volume("sell") == 0
        short_positions_volume_condition = self.get_positions_volume("sell") == 0
        short_check_time_pause_after_trade = self.check_time_pause_after_trade(
            self.fields.block_short_trade_until
        )
        if (
            short_orders_volume_condition
            and short_positions_volume_condition
            and short_condition_period
            and short_check_time_pause_after_trade
        ):
            order_sent = self.place_order("sell", timeframe)
            if order_sent:
                self.fields.block_short_trade_until = (
                    datetime.datetime.now()
                    + datetime.timedelta(
                        minutes=self.fields.short_pause_after_trade_min
                    )
                )
                short_condition_period = False

    def is_long_percent_to_entry_reached(self):
        # global price_difference_long_entry
        price_current = float(self.bybit.fetch_ticker(self.symbol)["ask"])
        price_ask_tick_some_time_ago = self.get_ask_tick_of_some_time_ago()
        percent_difference = self.calculate_percent_rising_price(
            price_ask_tick_some_time_ago, price_current
        )
        if (
            percent_difference < self.fields.price_difference_long_entry
            or price_ask_tick_some_time_ago == 0
            or price_current < price_ask_tick_some_time_ago
        ):
            return False
        return True

    def is_short_percent_to_entry_reached(self):
        # global price_difference_short_entry, only_buy

        price_current = float(self.bybit.fetch_ticker(self.symbol)["bid"])
        price_bid_tick_some_time_ago = self.get_bid_tick_of_some_time_ago()
        percent_difference = self.calculate_percent_rising_price(
            price_bid_tick_some_time_ago, price_current
        )
        if (
            percent_difference < self.fields.price_difference_short_entry
            or price_bid_tick_some_time_ago == 0
            or price_current > price_bid_tick_some_time_ago
        ):
            return False
        return True

    def calculate_percent_rising_price(self, prev_close, curr_close):
        return abs((curr_close - prev_close) / prev_close) * 100

    def get_bid_tick_of_some_time_ago(
        self,
    ):
        self.bybit.fetch_ohlcv(self.symbol)[-self.fields.short_period][1]
        return 0.0  # Implement this function to get the bid tick of some time ago

    def get_ask_tick_of_some_time_ago(self):
        self.bybit.fetch_ohlcv(self.symbol)[-self.fields.long_period][1]
        return 0.0  # Implement this function to get the ask tick of some time ago

    def get_positions_volume(self, order_type):
        volume = self.bybit.fetch_position(self.symbol)["contracts"]
        return volume

    def get_orders_volume(self, order_type):
        volume = 0.0
        for order in self.bybit.fetch_open_orders():
            if order["side"] == order_type:
                volume += float(order["info"]["volume"])
        return volume

    def place_order(self, order_type, timeframe):
        # global long_take_profit_percent, long_stop_loss_percent, long_entry_sum_in_dollars, short_take_profit_percent, short_stop_loss_percent, short_entry_sum_in_dollars
        curr_price = (
            float(self.bybit.fetch_ticker(self.symbol)["ask"])
            if order_type == "buy"
            else float(self.bybit.fetch_ticker(self.symbol)["bid"])
        )
        price_closed_candle = float(
            self.bybit.fetch_ohlcv(self.symbol, timeframe)[-1][4]
        )
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
        price_diff = self.calculate_percent_rising_price(
            price_closed_candle, curr_price
        )
        # if price_diff > order_opening_percent_limit:
        if price_diff > self.fields.price_difference_long_entry:
            return True

        order_params = {
            "symbol": self.symbol,
            "type": "market",
            "side": order_type,
            "amount": self.get_contract_size_volume(order_type),
            "params": {},
        }
        if order_type == "buy":
            order_params["params"]["takeProfit"] = curr_price + (
                curr_price * (take_profit_percent / 100)
            )
            order_params["params"]["stopLoss"] = curr_price - (
                curr_price * (stop_loss_percent / 100)
            )
        else:
            order_params["params"]["tp"] = curr_price - (
                curr_price * (take_profit_percent / 100)
            )
            order_params["params"]["sl"] = curr_price + (
                curr_price * (stop_loss_percent / 100)
            )
        order = self.bybit.create_order(**order_params)
        return (
            self.bybit.fetch_order(order["info"]["orderId"], self.symbol)["status"]
            == "closed"
        )

    def get_contract_size_volume(self, order_type):
        curr_price = (
            float(self.bybit.fetch_ticker(self.symbol)["ask"])
            if order_type == "buy"
            else float(self.bybit.fetch_ticker(self.symbol)["bid"])
        )
        leverage = int(self.bybit.fetch_position(self.symbol)["leverage"])
        entry_sum_in_dollars = (
            self.fields.long_entry_sum_in_dollars
            if order_type == "buy"
            else self.fields.short_entry_sum_in_dollars
        )
        return round((entry_sum_in_dollars / (curr_price) * leverage), 2)

    def check_time_pause_after_trade(block_trade_time):
        return block_trade_time < datetime.datetime.now()

    def trailing(self):
        global long_trailing_stop, short_trailing_stop
        positions = self.bybit.fetch_open_positions()
        for position in positions:
            symbol = position["symbol"]
            position_ticket = position["id"]
            trade_type = position["info"]["type"]
            if trade_type == "buy" and not self.fields.long_trailing_stop:
                bid = float(self.bybit.fetch_ticker(symbol)["bid"])
                if bid - float(position["info"]["entryPrice"]) > bid * (
                    long_trailing_stop / 100
                ):
                    if float(position["info"]["stopLoss"]) < bid - bid * (
                        long_trailing_stop / 100
                    ):
                        self.bybit.edit_position(
                            position_ticket,
                            {"stopLoss": bid - bid * (long_trailing_stop / 100)},
                        )

            elif trade_type == "sell" and not self.fields.short_trailing_stop:
                ask = float(self.bybit.fetch_ticker(symbol)["ask"])
                if float(position["info"]["entryPrice"]) - ask > ask * (
                    short_trailing_stop / 100
                ):
                    if (
                        float(position["info"]["stopLoss"])
                        > ask + ask * (short_trailing_stop / 100)
                        or float(position["info"]["stopLoss"]) == 0
                    ):
                        self.bybit.edit_position(
                            position_ticket,
                            {"stopLoss": ask + ask * (short_trailing_stop / 100)},
                        )

    def immidiate_trailing(self):
        # global long_trailing_stop, short_trailing_stop
        positions = self.bybit.fetch_open_positions()
        for position in positions:
            symbol = position["symbol"]
            position_ticket = position["id"]
            trade_type = position["info"]["type"]
            if trade_type == "buy" and self.fields.long_trailing_stop:
                bid = float(self.bybit.fetch_ticker(symbol)["bid"])
                if float(position["info"]["stopLoss"]) < bid - bid * (
                    long_trailing_stop / 100
                ):
                    self.bybit.edit_position(
                        position_ticket,
                        {"stopLoss": bid - bid * (long_trailing_stop / 100)},
                    )
            elif trade_type == "sell" and self.fields.short_trailing_stop:
                ask = float(self.bybit.fetch_ticker(symbol)["ask"])
                if (
                    float(position["info"]["stopLoss"])
                    > ask + ask * (short_trailing_stop / 100)
                    or float(position["info"]["stopLoss"]) == 0
                ):
                    self.bybit.edit_position(
                        position_ticket,
                        {"stopLoss": ask + ask * (short_trailing_stop / 100)},
                    )

    def run(self):
        # # Main loop
        while True:
            self.on_tick()
            time.sleep(10)

    def get_leverage(self, params):
        if params is None:
            params = {}

        position = self.bybit.fetch_position(
            symbol=self.symbol,
            params=(params | self._default_params),
        )
        if position:
            return float(position.get("info", {}).get("leverage", "0"))
        return None


if __name__ == "__main__":
    bot = Bot()
    while True:
        try:
            bot.run()
        except:
            print("Всё хорошо")

    print()
