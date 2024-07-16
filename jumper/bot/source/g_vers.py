import datetime
import time
from source.bybit import BybitModified


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
        self.trades = []

    def close_expired_orders_by_price_percent(self):
        for order in self.bybit.fetch_open_orders():

            open_order_price = self.bybit.fetch_position(self.symbol)["entryPrice"]
            if not open_order_price:
                continue
            order_type = order["type"]
            symbol_info = self.bybit.fetch_ticker(order["symbol"])

            bid_or_ask = (
                float(symbol_info["ask"])
                if order_type == "limit"
                else float(symbol_info["bid"])
            )
            price_diff = self.calculate_percent_rising_price(
                open_order_price, bid_or_ask
            )
            if self.symbol.rstrip("USDT") in order["symbol"]:
                continue
            if price_diff > self.fields.order_expiration_by_price_percent_limit:
                self.bybit.cancel_order(order["id"], order["symbol"])

    def on_tick(self):
        self.close_expired_orders_by_price_percent()
        self.trailing()
        # self.immidiate_trailing()

        long_condition_for_1m = self.is_long_percent_to_entry_reached()
        short_condition_for_1m = self.is_short_percent_to_entry_reached()

        self.express_long_condition("1m", long_condition_for_1m)
        self.express_short_condition("1m", short_condition_for_1m)

    def express_long_condition(self, timeframe, long_condition_period):
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
        return self.bybit.fetch_ohlcv(self.symbol)[-self.fields.short_period][1]

    def get_ask_tick_of_some_time_ago(self):
        return self.bybit.fetch_ohlcv(self.symbol)[-self.fields.long_period][1]

    def get_positions_volume(self, order_type):
        volume = self.bybit.fetch_position(self.symbol)["contracts"]
        return volume

    def get_orders_volume(self, order_type):
        volume = 0.0
        for order in self.bybit.fetch_open_orders():
            if order["side"] == order_type:
                volume += float(order["amount"])
        return volume

    def place_order(self, order_type, timeframe):
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
        order_params["id"] = order["id"]
        return (
            self.bybit.fetch_open_order(order["info"]["orderId"], self.symbol)["status"]
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

    def check_time_pause_after_trade(self, block_trade_time):
        return (
            True if not block_trade_time else block_trade_time < datetime.datetime.now()
        )

    def trailing(self):
        position = self.bybit.fetch_position(self.symbol)

        for order in self.bybit.fetch_open_orders():
            if order["stopLossPrice"]:
                symbol = order["symbol"]
                position_ticket = order["id"]

                bid = float(self.bybit.fetch_ticker(self.symbol)["bid"])
                if not position["entryPrice"]:
                    continue
                if bid - float(position["entryPrice"]) > bid * (
                    self.fields.long_trailing_stop / 100
                ):
                    if float(order["stopLossPrice"]) < bid - bid * (
                        self.fields.long_trailing_stop / 100
                    ):
                        self.bybit.edit_order(
                            position_ticket,
                            self.symbol,
                            order["type"],
                            order["side"],
                            params={
                                "stopLossPrice": bid
                                - bid * (self.fields.long_trailing_stop / 100)
                            },
                        )

                ask = float(self.bybit.fetch_ticker(symbol)["ask"])
                if float(position["entryPrice"]) - ask > ask * (
                    self.fields.short_trailing_stop / 100
                ):
                    if (
                        float(order["stopLossPrice"])
                        > ask + ask * (self.fields.short_trailing_stop / 100)
                        or float(order["stopLossPrice"]) == 0
                    ):
                        self.bybit.edit_order(
                            position_ticket,
                            self.symbol,
                            order["type"],
                            order["side"],
                            {
                                "stopLossPrice": ask
                                + ask * (self.fields.short_trailing_stop / 100)
                            },
                        )

    def immidiate_trailing(self):
        positions = self.bybit.fetch_position(self.symbol)
        for position in positions:
            symbol = position["symbol"]
            position_ticket = position["id"]
            trade_type = position["info"]["type"]
            if trade_type == "buy" and self.fields.long_trailing_stop:
                bid = float(self.bybit.fetch_ticker(symbol)["bid"])
                if float(position["info"]["stopLoss"]) < bid - bid * (
                    self.fields.long_trailing_stop / 100
                ):
                    self.bybit.edit_position(
                        position_ticket,
                        {
                            "stopLoss": bid
                            - bid * (self.fields.long_trailing_stop / 100)
                        },
                    )
            elif trade_type == "sell" and self.fields.short_trailing_stop:
                ask = float(self.bybit.fetch_ticker(symbol)["ask"])
                if (
                    float(position["info"]["stopLoss"])
                    > ask + ask * (self.fields.short_trailing_stop / 100)
                    or float(position["info"]["stopLoss"]) == 0
                ):
                    self.bybit.edit_position(
                        position_ticket,
                        {
                            "stopLoss": ask
                            + ask * (self.fields.short_trailing_stop / 100)
                        },
                    )

    def run(self):
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
    ...
    # bot = Bot(fields=Fields())
    # bot.run()
    # # bot.place_order('buy', '1m')
    # # bot.trailing()
    # # bot = Bot()
    # # while True:
    # #     try:
    # #         bot.run()
    # #     except:
    # #         print("Всё хорошо")
    #
    # print()
