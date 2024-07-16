from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    Optional,
    ParamSpec,
    TypeVar,
    Union,
    cast,
)

import ccxt.async_support as cctx
from ccxt.base.errors import ArgumentsRequired, BadRequest, InvalidOrder
from ccxt.base.precise import Precise
from source.grid_project.src.common.typedef import OrderSide, OrderType
from source.grid_project.src.utils.logger import Logger


logger = Logger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def bad_request_handler(f: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
    async def _wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        try:
            return await f(*args, **kwargs)
        except BadRequest as err:
            logger.exception(msg="Error has occured while sending order", exc_info=err)
            return cast(T, {})

    return _wrapper


class BybitModified(cctx.bybit):
    @bad_request_handler
    async def create_order(  # noqa: C901
        self,
        symbol: str,
        type: OrderType,
        side: OrderSide,
        amount: Union[int, float],
        price: Optional[float] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> Any:
        if params is None:
            params = {}

        await self.load_markets()
        market = self.market(symbol)
        symbol = market["symbol"]
        enableUnifiedMargin, enableUnifiedAccount = await self.is_unified_enabled()
        isUnifiedAccount = enableUnifiedMargin or enableUnifiedAccount
        isUsdcSettled = market["settle"] == "USDC"
        if isUsdcSettled and not isUnifiedAccount:
            return await self.create_usdc_order(
                symbol, type, side, amount, price, params
            )
        lowerCaseType = type.lower()
        if (price is None) and (lowerCaseType == "limit"):
            raise ArgumentsRequired(
                self.id + " createOrder requires a price argument for limit orders"
            )
        request = {
            "symbol": market["id"],
            "side": self.capitalize(side),
            "orderType": self.capitalize(lowerCaseType),  # limit or market
        }
        if market["spot"]:
            request["category"] = "spot"
        elif market["linear"]:
            request["category"] = "linear"
        elif market["inverse"]:
            request["category"] = "inverse"
        elif market["option"]:
            request["category"] = "option"
        if market["spot"] and (type == "market") and (side == "buy"):
            if self.options["createMarketBuyOrderRequiresPrice"]:
                cost = self.safe_number(params, "cost")
                params = self.omit(params, "cost")
                if price is None and cost is None:
                    raise InvalidOrder(
                        self.id
                        + " createOrder() requires the price argument with market buy"
                        " orders to calculate total order cost(amount to spend),"
                        " where cost = amount * price. Supply a price argument to"
                        " createOrder() call if you want the cost to be calculated"
                        " for you from price and amount, or, alternatively, add"
                        ' .options["createMarketBuyOrderRequiresPrice"] = False to'
                        " supply the cost in the amount argument(the"
                        " exchange-specific behaviour)"
                    )
                else:
                    amountString = self.number_to_string(amount)
                    priceString = self.number_to_string(price)
                    quoteAmount = Precise.string_mul(amountString, priceString)
                    amount = (
                        cost if (cost is not None) else self.parse_number(quoteAmount)
                    )
                    request["qty"] = self.cost_to_precision(symbol, amount)
            else:
                request["qty"] = self.cost_to_precision(symbol, amount)
        else:
            request["qty"] = self.amount_to_precision(symbol, amount)
        isMarket = lowerCaseType == "market"
        isLimit = lowerCaseType == "limit"
        if isLimit:
            request["price"] = self.price_to_precision(symbol, price)
        timeInForce = self.safe_string_lower(
            params, "timeInForce"
        )  # self is same specific param
        postOnly = None
        postOnly, params = self.handle_post_only(
            isMarket, timeInForce == "postonly", params
        )
        if postOnly:
            request["timeInForce"] = "PostOnly"
        elif timeInForce == "gtc":
            request["timeInForce"] = "GTC"
        elif timeInForce == "fok":
            request["timeInForce"] = "FOK"
        elif timeInForce == "ioc":
            request["timeInForce"] = "IOC"
        triggerPrice = self.safe_value_2(params, "triggerPrice", "stopPrice")
        stopLossTriggerPrice = self.safe_value(params, "stopLossPrice")
        takeProfitTriggerPrice = self.safe_value(params, "takeProfitPrice")
        stopLoss = self.safe_value(params, "stopLoss")
        takeProfit = self.safe_value(params, "takeProfit")
        isStopLossTriggerOrder = stopLossTriggerPrice is not None
        isTakeProfitTriggerOrder = takeProfitTriggerPrice is not None
        isStopLoss = stopLoss is not None
        isTakeProfit = takeProfit is not None
        isBuy = side == "buy"
        setTriggerDirection = (
            not isBuy if (stopLossTriggerPrice or triggerPrice) else isBuy
        )
        defaultTriggerDirection = 2 if setTriggerDirection else 1
        triggerDirection = self.safe_string(params, "triggerDirection")
        params = self.omit(params, "triggerDirection")
        selectedDirection = defaultTriggerDirection
        if triggerDirection is not None:
            isAsending = (triggerDirection == "up") or (triggerDirection == "1")
            selectedDirection = 1 if isAsending else 2
        if triggerPrice is not None:
            request["triggerDirection"] = selectedDirection
            request["triggerPrice"] = self.price_to_precision(symbol, triggerPrice)
        elif isStopLossTriggerOrder or isTakeProfitTriggerOrder:
            request["triggerDirection"] = selectedDirection
            triggerPrice = (
                stopLossTriggerPrice
                if isStopLossTriggerOrder
                else takeProfitTriggerPrice
            )
            request["triggerPrice"] = self.price_to_precision(symbol, triggerPrice)
            request["reduceOnly"] = True
        if isStopLoss or isTakeProfit:
            if isStopLoss:
                slTriggerPrice = self.safe_value_2(
                    stopLoss, "triggerPrice", "stopPrice", stopLoss
                )
                request["stopLoss"] = self.price_to_precision(symbol, slTriggerPrice)
            if isTakeProfit:
                tpTriggerPrice = self.safe_value_2(
                    takeProfit, "triggerPrice", "stopPrice", takeProfit
                )
                request["takeProfit"] = self.price_to_precision(symbol, tpTriggerPrice)
        if market["spot"]:
            # only works for spot market
            if triggerPrice is not None:
                request["orderFilter"] = "StopOrder"
            elif (
                stopLossTriggerPrice is not None
                or takeProfitTriggerPrice is not None
                or isStopLoss
                or isTakeProfit
            ):
                request["orderFilter"] = "tpslOrder"
        clientOrderId = self.safe_string(params, "clientOrderId")
        if clientOrderId is not None:
            request["orderLinkId"] = clientOrderId
        elif market["option"]:
            # mandatory field for options
            request["orderLinkId"] = self.uuid16()
        params = self.omit(
            params,
            [
                "stopPrice",
                "timeInForce",
                "stopLossPrice",
                "takeProfitPrice",
                "postOnly",
                "clientOrderId",
                "triggerPrice",
                "stopLoss",
                "takeProfit",
            ],
        )
        response = await self.privatePostV5OrderCreate(self.extend(request, params))
        order = self.safe_value(response, "result", {})
        return self.parse_order(order, market)
