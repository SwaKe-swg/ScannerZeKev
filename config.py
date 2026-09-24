import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


def _env_bool(key: str, default: str = "0") -> bool:
    return os.getenv(key, default).strip().lower() in ("1", "true", "yes", "on")


class Config:
    BOT_VERSION = os.getenv("BOT_VERSION", "2.3")
    REAL_TRADING = False  # HARD LOCK — paper only
    SOLANA_PRIVATE_KEY = os.getenv("SOLANA_PRIVATE_KEY", "")

    # ~100 EUR paper @ SOL/EUR ≈ 102.16 → ~0.979 SOL
    VIRTUAL_SOL_BALANCE = float(os.getenv("VIRTUAL_SOL_BALANCE", "0.98"))
    # TRADE_SIZE_SOL alias supported
    TRADE_AMOUNT_SOL = float(
        os.getenv("TRADE_AMOUNT_SOL")
        or os.getenv("TRADE_SIZE_SOL")
        or "0.02"
    )

    SLIPPAGE_BPS = int(os.getenv("SLIPPAGE_BPS", "150"))
    ESTIMATED_FEE_SOL = float(os.getenv("ESTIMATED_FEE_SOL", "0.0015"))

    TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "35.0"))
    STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "-15.0"))
    MAX_OPEN_POSITIONS = int(os.getenv("MAX_OPEN_POSITIONS", "2"))
    COOLDOWN_SECONDS = int(os.getenv("COOLDOWN_SECONDS", "90"))

    MIN_LIQUIDITY = float(os.getenv("MIN_LIQUIDITY", "12000"))
    MAX_MARKET_CAP = float(os.getenv("MAX_MARKET_CAP", "250000"))
    MIN_MARKET_CAP = float(os.getenv("MIN_MARKET_CAP", "20000"))
    MIN_HOLDERS = int(os.getenv("MIN_HOLDERS", "10"))
    MIN_BUYS_M5 = int(os.getenv("MIN_BUYS_M5", "8"))
    MIN_BUY_SELL_RATIO = float(os.getenv("MIN_BUY_SELL_RATIO", "1.2"))
    MIN_VOLUME_M5 = float(os.getenv("MIN_VOLUME_M5", "2000"))
    MIN_ENTRY_SCORE = int(os.getenv("MIN_ENTRY_SCORE", "70"))
    # NP lesson: never-green / falling knife — require real 5m strength
    MIN_PRICE_CHANGE_M5 = float(os.getenv("MIN_PRICE_CHANGE_M5", "3.0"))
    MAX_PRICE_CHANGE_M5 = float(os.getenv("MAX_PRICE_CHANGE_M5", "80.0"))
    BLACKLIST_HOURS = float(os.getenv("BLACKLIST_HOURS", "6.0"))
    MAX_SYMBOL_LENGTH = int(os.getenv("MAX_SYMBOL_LENGTH", "12"))
    MAX_AGE_MINUTES = int(os.getenv("MAX_AGE_MINUTES", "180"))
    REQUIRE_SOCIALS = _env_bool("REQUIRE_SOCIALS", "0")

    # Anti-scam / on-chain
    CHECK_MINT_AUTHORITY = _env_bool("CHECK_MINT_AUTHORITY", "1")
    CHECK_FREEZE_AUTHORITY = _env_bool(
        "CHECK_FREEZE_AUTHORITY",
        os.getenv("CHECK_FREEZE", "1"),
    )
    CHECK_FREEZE = CHECK_FREEZE_AUTHORITY  # alias
    CHECK_TRANSFER_FEE = _env_bool("CHECK_TRANSFER_FEE", "1")
    MAX_TRANSFER_FEE_PCT = float(os.getenv("MAX_TRANSFER_FEE_PCT", "5.0"))
    CHECK_TOP_HOLDER = _env_bool("CHECK_TOP_HOLDER", "1")
    MAX_TOP_HOLDER_PCT = float(os.getenv("MAX_TOP_HOLDER_PCT", "20.0"))
    CHECK_LIQ_MC_RATIO = _env_bool("CHECK_LIQ_MC_RATIO", "1")
    MIN_LIQ_MC_RATIO = float(os.getenv("MIN_LIQ_MC_RATIO", "0.10"))
    CHECK_HONEYPOT_ZERO_SELLS = _env_bool("CHECK_HONEYPOT_ZERO_SELLS", "1")
    HONEYPOT_ZERO_SELL_BUYS = int(os.getenv("HONEYPOT_ZERO_SELL_BUYS", "25"))
    REQUIRE_MOMENTUM_BUY_CONSISTENCY = _env_bool("REQUIRE_MOMENTUM_BUY_CONSISTENCY", "1")

    USE_RUGCHECK = _env_bool("USE_RUGCHECK", "1")
    USE_ONCHAIN_CHECKS = _env_bool("USE_ONCHAIN_CHECKS", "1")
    USE_ANTI_SCAM_ENGINE = _env_bool("USE_ANTI_SCAM_ENGINE", "1")
    FAIL_CLOSED_ONCHAIN = _env_bool("FAIL_CLOSED_ONCHAIN", "1")
    FAIL_CLOSED_RUGCHECK = _env_bool("FAIL_CLOSED_RUGCHECK", "0")
    FAIL_CLOSED_LP = _env_bool("FAIL_CLOSED_LP", "0")
    REQUIRE_LP_LOCKED_OR_BURNED = _env_bool("REQUIRE_LP_LOCKED_OR_BURNED", "0")
    CHECK_RUGCHECK_HONEYPOT = _env_bool("CHECK_RUGCHECK_HONEYPOT", "1")
    CHECK_RUGCHECK_RENOUNCED = _env_bool("CHECK_RUGCHECK_RENOUNCED", "1")
    CHECK_RUGCHECK_SCORE = _env_bool("CHECK_RUGCHECK_SCORE", "1")
    CHECK_RUGCHECK_DANGER = _env_bool("CHECK_RUGCHECK_DANGER", "1")
    MAX_RUGCHECK_RAW_SCORE = int(os.getenv("MAX_RUGCHECK_RAW_SCORE", "1500"))

    # NP lesson: confirm entry still green after delay
    CONFIRM_ENTRY = _env_bool("CONFIRM_ENTRY", "1")
    CONFIRM_ENTRY_SECONDS = float(os.getenv("CONFIRM_ENTRY_SECONDS", "20"))
    CONFIRM_MAX_DRAWDOWN_PCT = float(os.getenv("CONFIRM_MAX_DRAWDOWN_PCT", "5.0"))
    FAIL_CLOSED_CONFIRM = _env_bool("FAIL_CLOSED_CONFIRM", "1")

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

    JUPITER_PRICE_API = os.getenv(
        "JUPITER_PRICE_API", "https://api.jup.ag/price/v2"
    )

    DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"
    DEXSCREENER_WS_URL = os.getenv(
        "DEXSCREENER_WS_URL", "wss://io.dexscreener.com/ws/solana/pairs"
    )
