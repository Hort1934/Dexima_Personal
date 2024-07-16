from typing import Dict, Union, Optional


def get_custom_ranges(
    params: Dict[str, Union[Optional[int], str, bool, float]]
) -> Dict[str, dict]:
    custom_ranges = {}

    # Define custom ranges for each parameter based on the provided params
    if params.get("long_period")["checked"]:
        custom_ranges["long_period"] = {
            "from": float(params["long_period"]["long_period_start"]),
            "to": float(params["long_period"]["long_period_end"]),
            "step": float(params["long_period"]["long_period_step"]),
        }
    else:
        custom_ranges["long_period"] = float(params.get("long_period", 0)["value"])
    if params.get("short_period")["checked"]:
        custom_ranges["short_period"] = {
            "from": float(params["short_period"]["short_period_start"]),
            "to": float(params["short_period"]["short_period_end"]),
            "step": float(params["short_period"]["short_period_step"]),
        }
    else:
        custom_ranges["short_period"] = float(params.get("short_period", 0)["value"])

    if params.get("long_entry_sum_in_dollars")["checked"]:
        custom_ranges["long_entry_sum_in_dollars"] = {
            "from": float(
                params["long_entry_sum_in_dollars"]["long_entry_sum_in_dollars_start"]
            ),
            "to": float(
                params["long_entry_sum_in_dollars"]["long_entry_sum_in_dollars_end"]
            ),
            "step": float(
                params["long_entry_sum_in_dollars"]["long_entry_sum_in_dollars_step"]
            ),
        }
    else:
        custom_ranges["long_entry_sum_in_dollars"] = float(
            params.get("long_entry_sum_in_dollars", 500)["value"]
        )

    if params.get("short_entry_sum_in_dollars")["checked"]:
        custom_ranges["short_entry_sum_in_dollars"] = {
            "from": float(
                params["short_entry_sum_in_dollars"]["short_entry_sum_in_dollars_start"]
            ),
            "to": float(
                params["short_entry_sum_in_dollars"]["short_entry_sum_in_dollars_end"]
            ),
            "step": float(
                params["short_entry_sum_in_dollars"]["short_entry_sum_in_dollars_step"]
            ),
        }
    else:
        custom_ranges["short_entry_sum_in_dollars"] = float(
            params.get("short_entry_sum_in_dollars", 500)["value"]
        )

    if params.get("long_take_profit_percent")["checked"]:
        custom_ranges["long_take_profit_percent"] = {
            "from": float(
                params["long_take_profit_percent"]["long_take_profit_percent_start"]
            ),
            "to": float(
                params["long_take_profit_percent"]["long_take_profit_percent_end"]
            ),
            "step": float(
                params["long_take_profit_percent"]["long_take_profit_percent_step"]
            ),
        }
    else:
        custom_ranges["long_take_profit_percent"] = float(
            params.get("long_take_profit_percent", 50)["value"]
        )

    if params.get("long_stop_loss_percent")["checked"]:
        custom_ranges["long_stop_loss_percent"] = {
            "from": float(
                params["long_stop_loss_percent"]["long_stop_loss_percent_start"]
            ),
            "to": float(params["long_stop_loss_percent"]["long_stop_loss_percent_end"]),
            "step": float(
                params["long_stop_loss_percent"]["long_stop_loss_percent_step"]
            ),
        }
    else:
        custom_ranges["long_stop_loss_percent"] = float(
            params.get("long_stop_loss_percent", 5)["value"]
        )

    if params.get("short_take_profit_percent")["checked"]:
        custom_ranges["short_take_profit_percent"] = {
            "from": float(
                params["short_take_profit_percent"]["short_take_profit_percent_start"]
            ),
            "to": float(
                params["short_take_profit_percent"]["short_take_profit_percent_end"]
            ),
            "step": float(
                params["short_take_profit_percent"]["short_take_profit_percent_step"]
            ),
        }
    else:
        custom_ranges["short_take_profit_percent"] = float(
            params.get("short_take_profit_percent", 50)["value"]
        )

    if params.get("short_stop_loss_percent")["checked"]:
        custom_ranges["short_stop_loss_percent"] = {
            "from": float(
                params["short_stop_loss_percent"]["short_stop_loss_percent_start"]
            ),
            "to": float(params["short_stop_loss_percent"]["short_stop_loss_percent_end"]),
            "step": float(
                params["short_stop_loss_percent"]["short_stop_loss_percent_step"]
            ),
        }
    else:
        custom_ranges["short_stop_loss_percent"] = float(
            params.get("short_stop_loss_percent", 5)["value"]
        )

    if params.get("price_difference_long_entry")["checked"]:
        custom_ranges["price_difference_long_entry"] = {
            "from": float(
                params["price_difference_long_entry"][
                    "price_difference_long_entry_start"
                ]
            ),
            "to": float(
                params["price_difference_long_entry"]["price_difference_long_entry_end"]
            ),
            "step": float(
                params["price_difference_long_entry"][
                    "price_difference_long_entry_step"
                ]
            ),
        }
    else:
        custom_ranges["price_difference_long_entry"] = float(
            params.get("price_difference_long_entry", 0.1)["value"]
        )

    if params.get("price_difference_short_entry")["checked"]:
        custom_ranges["price_difference_short_entry"] = {
            "from": float(
                params["price_difference_short_entry"][
                    "price_difference_short_entry_start"
                ]
            ),
            "to": float(
                params["price_difference_short_entry"][
                    "price_difference_short_entry_end"
                ]
            ),
            "step": float(
                params["price_difference_short_entry"][
                    "price_difference_short_entry_step"
                ]
            ),
        }
    else:
        custom_ranges["price_difference_short_entry"] = float(
            params.get("price_difference_short_entry", 0.1)["value"]
        )

    if params.get("block_long_trade_until"):
        custom_ranges["block_long_trade_until"] = {
            "from": float(
                params["block_long_trade_until"]["block_long_trade_until_start"]
            ),
            "to": float(params["block_long_trade_until"]["block_long_trade_until_end"]),
            "step": float(
                params["block_long_trade_until"]["block_long_trade_until_step"]
            ),
        }
    else:
        custom_ranges["block_long_trade_until"] = params.get(
            "block_long_trade_until", None
        )

    if params.get("block_short_trade_until"):
        custom_ranges["block_short_trade_until"] = {
            "from": float(
                params["block_short_trade_until"]["block_short_trade_until_start"]
            ),
            "to": float(params["block_short_trade_until"]["block_short_trade_until_end"]),
            "step": float(
                params["block_short_trade_until"]["block_short_trade_until_step"]
            ),
        }
    else:
        custom_ranges["block_short_trade_until"] = params.get(
            "block_short_trade_until", None
        )

    if params.get("long_pause_after_trade_min")["checked"]:
        custom_ranges["long_pause_after_trade_min"] = {
            "from": float(
                params["long_pause_after_trade_min"]["long_pause_after_trade_min_start"]
            ),
            "to": float(
                params["long_pause_after_trade_min"]["long_pause_after_trade_min_end"]
            ),
            "step": float(
                params["long_pause_after_trade_min"]["long_pause_after_trade_min_step"]
            ),
        }
    else:
        custom_ranges["long_pause_after_trade_min"] = float(
            params.get("long_pause_after_trade_min", 1)["value"]
        )

    if params.get("short_pause_after_trade_min")["checked"]:
        custom_ranges["short_pause_after_trade_min"] = {
            "from": float(
                params["short_pause_after_trade_min"][
                    "short_pause_after_trade_min_start"
                ]
            ),
            "to": float(
                params["short_pause_after_trade_min"]["short_pause_after_trade_min_end"]
            ),
            "step": float(
                params["short_pause_after_trade_min"][
                    "short_pause_after_trade_min_step"
                ]
            ),
        }
    else:
        custom_ranges["short_pause_after_trade_min"] = float(
            params.get("short_pause_after_trade_min", 1)["value"]
        )

    if params.get("order_expiration_by_price_percent_limit")["checked"]:
        custom_ranges["order_expiration_by_price_percent_limit"] = {
            "from": float(
                params["order_expiration_by_price_percent_limit"][
                    "order_expiration_by_price_percent_limit_start"
                ]
            ),
            "to": float(
                params["order_expiration_by_price_percent_limit"][
                    "order_expiration_by_price_percent_limit_end"
                ]
            ),
            "step": float(
                params["order_expiration_by_price_percent_limit"][
                    "order_expiration_by_price_percent_limit_step"
                ]
            ),
        }
    else:
        custom_ranges["order_expiration_by_price_percent_limit"] = float(
            params.get("order_expiration_by_price_percent_limit", 5)["value"]
        )

    if params.get("long_trailing_stop")["checked"]:
        custom_ranges["long_trailing_stop"] = {
            "from": float(params["long_trailing_stop"]["long_trailing_stop_start"]),
            "to": float(params["long_trailing_stop"]["long_trailing_stop_end"]),
            "step": float(params["long_trailing_stop"]["long_trailing_stop_step"]),
        }
    else:
        custom_ranges["long_trailing_stop"] = float(
            params.get("long_trailing_stop", 0.1)["value"]
        )

    if params.get("short_trailing_stop")["checked"]:
        custom_ranges["short_trailing_stop"] = {
            "from": float(params["short_trailing_stop"]["short_trailing_stop_start"]),
            "to": float(params["short_trailing_stop"]["short_trailing_stop_end"]),
            "step": float(params["short_trailing_stop"]["short_trailing_stop_step"]),
        }
    else:
        custom_ranges["short_trailing_stop"] = float(
            params.get("short_trailing_stop", 0.1)["value"]
        )
    custom_ranges['LEVERAGE'] = params['Leverage']
    return custom_ranges
