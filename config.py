import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


class Config:
    REAL_TRADING = False
    SOLANA_PRIVATE_KEY = os.getenv("SOLANA_PRIVATE_KEY", "")

    VIRTUAL_SOL_BALANCE = float(os.getenv("VIRTUAL_SOL_BALANCE", "0.30"))
    TRADE_AMOUNT_SOL = float(os.getenv("TRADE_AMOUNT_SOL", "0.015"))

    SLIPPAGE_BPS = int(os.getenv("SLIPPAGE_BPS", "150"))
    ESTIMATED_FEE_SOL = float(os.getenv("ESTIMATED_FEE_SOL", "0.0015"))

    # Risk: win earlier, cut sooner, few concurrent bets
    TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "35.0"))
    STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "-15.0"))
    MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "2"))
    COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "90"))

    # Hard filters (research: reject most junk before buy)
    MIN_LIQUIDITY = float(os.getenv("MIN_LIQUIDITY", "12000"))
    MAX_MARKET_CAP = float(os.getenv("MAX_MARKET_CAP", "250000"))
    MIN_MARKET_CAP = float(os.getenv("MIN_MARKET_CAP", "20000"))
    MIN_HOLDERS = int(os.getenv("MIN_HOLDERS", "10"))
    MIN_BUYS_M5 = int(os.getenv("MIN_BUYS_M5", "8"))
    MIN_BUY_SELL_RATIO = float(os.getenv("MIN_BUY_SELL_RATIO", "1.2"))
    MIN_VOLUME_M5 = float(os.getenv("MIN_VOLUME_M5", "2000"))
    MIN_ENTRY_SCORE = int(os.getenv("MIN_ENTRY_SCORE", "70"))
    MIN_PRICE_CHANGE_M5 = float(os.getenv("MIN_PRICE_CHANGE_M5", "2.0"))
    MAX_PRICE_CHANGE_M5 = float(os.getenv("MAX_PRICE_CHANGE_M5", "80.0"))
    BLACKLIST_HOURS = float(os.getenv("BLACKLIST_HOURS", "6.0"))
    MAX_SYMBOL_LENGTH = int(os.getenv("MAX_SYMBOL_LENGTH", "12"))
    MAX_AGE_MINUTES = int(os.getenv("MAX_AGE_MINUTES", "180"))
    REQUIRE_SOCIALS = os.getenv("REQUIRE_SOCIALS", "0") == "1"

    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
    HELIUS_RPC_URL = (
        os.getenv("HELIUS_RPC_URL")
        or (
            f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
            if HELIUS_API_KEY
            else ""
        )
    )

    DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"
    DEXSCREENER_WS_URL = os.getenv(
        "DEXSCREENER_WS_URL", "wss://io.dexscreener.com/ws/solana/pairs"
    )
