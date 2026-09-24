import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")


class Config:
    # --- MODALITA TRADING ---
    REAL_TRADING = False
    SOLANA_PRIVATE_KEY = os.getenv("SOLANA_PRIVATE_KEY", "")

    # --- PARAMETRI DI BUDGET ---
    VIRTUAL_SOL_BALANCE = float(os.getenv("VIRTUAL_SOL_BALANCE", "0.30"))
    TRADE_AMOUNT_SOL = float(os.getenv("TRADE_AMOUNT_SOL", "0.02"))

    # --- PROTEZIONE REALE (SLIPPAGE & FEES) ---
    SLIPPAGE_BPS = int(os.getenv("SLIPPAGE_BPS", "150"))
    ESTIMATED_FEE_SOL = float(os.getenv("ESTIMATED_FEE_SOL", "0.0015"))

    # --- TARGET PROFIT E LOSS ---
    TAKE_PROFIT_PCT = float(os.getenv("TAKE_PROFIT_PCT", "50.0"))
    STOP_LOSS_PCT = float(os.getenv("STOP_LOSS_PCT", "-12.0"))

    # --- TELEGRAM ---
    TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

    # --- RPC HELIUS ---
    HELIUS_API_KEY = os.getenv("HELIUS_API_KEY", "")
    HELIUS_RPC_URL = (
        os.getenv("HELIUS_RPC_URL")
        or (
            f"https://mainnet.helius-rpc.com/?api-key={HELIUS_API_KEY}"
            if HELIUS_API_KEY
            else ""
        )
    )

    # --- API PREZZI ---
    DEXSCREENER_API = "https://api.dexscreener.com/latest/dex/tokens/"
    DEXSCREENER_WS_URL = os.getenv(
        "DEXSCREENER_WS_URL", "wss://io.dexscreener.com/ws/solana/pairs"
    )

    MIN_LIQUIDITY = float(os.getenv("MIN_LIQUIDITY", "5000"))
    MAX_MARKET_CAP = float(os.getenv("MAX_MARKET_CAP", "50000"))
    MAX_AGE_MINUTES = int(os.getenv("MAX_AGE_MINUTES", "5"))
    MIN_HOLDERS = int(os.getenv("MIN_HOLDERS", "10"))
