from functools import cache
from pathlib import Path
from typing import Optional, Union

from pydantic_settings import BaseSettings


# class DatabaseSettings(BaseSettings):
#     host: str
#     port: int
#     user: str
#     password: str
#     db: str
#
#     model_config = SettingsConfigDict(
#         env_file=Path(__file__).parent.parent.parent / ".env",
#         env_file_encoding="utf-8",
#         case_sensitive=False,
#         env_prefix="POSTGRES_",
#     )
#
#
# class BybitSettings(BaseSettings):
#     api_key: str
#     api_secret: str
#
#     api_key_testnet: str
#     api_secret_testnet: str
#
#     fee: float = 0.01  # fee in percent (0.01%)
#
#     model_config = SettingsConfigDict(
#         env_file=Path(__file__).parent.parent.parent / ".env",
#         env_file_encoding="utf-8",
#         case_sensitive=False,
#         env_prefix="BYBIT_",
#     )


class Settings(BaseSettings):
    # db: DatabaseSettings = DatabaseSettings()  # type: ignore[call-arg]
    # bybit: BybitSettings = BybitSettings()  # type: ignore[call-arg]

    @staticmethod
    def root_dir() -> Path:
        return Path(__file__).resolve().parent.parent.parent

    @staticmethod
    def path(
        *paths: Union[str, Path],
        root_dir: Optional[Path] = None,
    ) -> Path:
        if root_dir is None:
            root_dir = Settings.root_dir()
        return Path(root_dir, *paths)


@cache
def load_settings() -> Settings:
    return Settings()
