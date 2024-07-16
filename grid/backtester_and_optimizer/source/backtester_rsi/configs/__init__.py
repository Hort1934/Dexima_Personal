import os
from dotenv import load_dotenv

load_dotenv()

YAHOO_PERIOD = os.getenv("YAHOO_PERIOD", "1mo")
YAHOO_INTERVAL = os.getenv("YAHOO_INTERVAL", "1m")

BALANCE = float(os.getenv("BALANCE", "1000.0"))
MARGIN = float(os.getenv("MARGIN", "260.0"))
