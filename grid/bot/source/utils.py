import base64
import binascii
import os

from typing import Union
from Crypto.Cipher import AES
from django.db import connections


class AESCipher:
    def __init__(self, key: Union[str, bytes]) -> None:
        self.__key = key

    @staticmethod
    def _resolve_key(
        key: Union[str, bytes, bytearray, memoryview]
    ) -> Union[bytes, bytearray, memoryview]:
        try:
            decrypted = list(base64.b64decode(key).decode())
        except binascii.Error:
            return key.encode() if isinstance(key, str) else key
        return base64.b64decode("".join(reversed(decrypted)))

    def encrypt(self, plain_text: str) -> str:
        cipher = AES.new(self._resolve_key(self.__key), AES.MODE_CFB)
        result = list(
            base64.b64encode(cipher.iv + cipher.encrypt(plain_text.encode())).decode()  # type: ignore
        )
        return "".join(reversed(result))

    def decrypt(self, hashed_text: str) -> str:
        data = list(hashed_text)
        decrypted = base64.b64decode("".join(reversed(data)))
        cipher = AES.new(self._resolve_key(self.__key), AES.MODE_CFB, iv=decrypted[:16])  # type: ignore
        return cipher.decrypt(decrypted[16:]).decode()  # type: ignore


def get_user_bybit_credentials(user_id):
    print(user_id)
    table_name = "main_service_bybitapicredentials"
    salt = base64.b64decode(os.getenv("KEY_SALT"))
    print(salt)
    with connections["postgres"].cursor() as cursor_postgres:
        cursor_postgres.execute(
            f"SELECT * FROM {table_name} WHERE user_id = %s", [user_id]
        )
        result_postgres = cursor_postgres.fetchall()
        salt = base64.b64decode(os.getenv("KEY_SALT"))
        aes = AESCipher(salt)
        api_key = aes.decrypt(result_postgres[0][1])
        secret_key = aes.decrypt(result_postgres[0][2])
        return api_key, secret_key


def get_user_username(user_id):
    table_name = "main_service_customuser"
    with connections["postgres"].cursor() as cursor_postgres:
        cursor_postgres.execute(
            f"SELECT username FROM {table_name} WHERE id = %s", [user_id]
        )
        return cursor_postgres.fetchone()[0]


def close_user_position_and_orders(api_key, api_secret, symbol, side, quantity):
    """close orders"""
    try:
        send_signed_default_request(
            "DELETE",
            "/fapi/v1/allOpenOrders",
            api_key=api_key,
            api_secret=api_secret,
            payload={"symbol": symbol},
        )
    except Exception as ex:
        return ex

    params_for_post_close_failed_position = {
        "symbol": symbol,
        "side": side,
        "type": "MARKET",
        "quantity": quantity,
    }
    """close position"""
    send_signed_default_request(
        "POST",
        ORDER_ENDPOINT,
        api_key,
        api_secret,
        params_for_post_close_failed_position,
    )
