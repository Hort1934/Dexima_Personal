from source.grid_project.src.common.executor.ccxt_base import CCXTCryptoExecutor
from source.grid_project.src.utils.bybit import BybitModified


class BybitExecutor(CCXTCryptoExecutor):
    def __init__(
        self,
        api_key: str,
        api_secret: str,
    ) -> None:
        super().__init__(BybitModified, api_key, api_secret)
