from binance.client import Client
import os

from dotenv import load_dotenv

load_dotenv()

api_key = os.getenv("API_KEY")
api_secret = os.getenv("API_SECRET")
client = Client(api_key, api_secret)
POSTGRES_HOST = os.getenv("POSTGRES_HOST")
POSTGRES_DB = os.getenv("POSTGRES_DB")
POSTGRES_USER = os.getenv("POSTGRES_USER")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD")
POSTGRES_PORT = os.getenv("POSTGRES_PORT")

# 314-DB2Range
ASSETS_POSTGRES_HOST = os.getenv("ASSETS_POSTGRES_HOST")
ASSETS_POSTGRES_DB = os.getenv("ASSETS_POSTGRES_DB")
ASSETS_POSTGRES_USER = os.getenv("ASSETS_POSTGRES_USER")
ASSETS_POSTGRES_PASSWORD = os.getenv("ASSETS_POSTGRES_PASSWORD")
ASSETS_POSTGRES_PORT = os.getenv("ASSETS_POSTGRES_PORT")
# 314-DB2Range

MERCHANT_ID = os.getenv("MERCHANT_ID")
MERCHANT_SECRET_KEY = os.getenv("MERCHANT_SECRET_KEY")
BACKTEST_COST = os.getenv("BACKTEST_COST")
OPTIMIZATION_COST = os.getenv("OPTIMIZATION_COST")

GRID_SERVICE = os.getenv("GRID_SERVICE")
JUMPER_SERVICE = os.getenv("JUMPER_SERVICE")
GRID_BOT = os.getenv("GRID_BOT")
JUMPER_BOT = os.getenv("JUMPER_BOT")

EXPO_GRID_START_BOT = GRID_BOT + "/grid-bot-service/start_grid_bot/"
EXPO_GRID_STOP_BOT = GRID_BOT + "/grid-bot-service/stop_grid_bot/"
EXPO_GRID_BACKTEST = GRID_SERVICE + "/api/backtest_and_optimizer_api/grid_backtest/"
EXPO_GRID_OPTIMIZATION = GRID_SERVICE + "/api/backtest_and_optimizer_api/grid_optimize/"

JUMPER_START_BOT = JUMPER_BOT + "/jumper_service/start_jumper_bot/"
JUMPER_STOP_BOT = JUMPER_BOT + "/jumper_service/stop_jumper_bot/"
JUMPER_BACKTEST = JUMPER_SERVICE + "/api/backtest_and_optimizer/jumper_backtest/"
JUMPER_OPTIMIZATION = JUMPER_SERVICE + "/api/backtest_and_optimizer/jumper_optimize/"
