from flask import Flask
app = Flask(__name__)

import asyncio
import logging
import httpx

from config import Config
from anti_rug_engine import AntiRugEngine
from risk_manager import PositionManager

try:
    from telegram_ui import build_trading_links_text
except ImportError:
    def build_trading_links_text(token_address: str) -> str:
        return f"🔗 <a href='https://dexscreener.com/solana/{token_address}'>DexScreener</a>"

from listeners.dex_listener import start_dex_listener
from listeners.twitter_listener import start_twitter_listener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

helius_url = getattr(Config, "HELIUS_RPC_URL", "")
anti_rug = AntiRugEngine(rpc_url=helius_url)

virtual_wallet = PositionManager(
    initial_balance=getattr(Config, "VIRTUAL_SOL_BALANCE", 0.30),
    trade_amount=getattr(Config, "TRADE_AMOUNT_SOL", 0.03)
)

async def send_telegram_msg(client: httpx.AsyncClient, text: str):
    token = getattr(Config, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(Config, "TELEGRAM_CHAT_ID", "")
    if not token or "IL_TUO" in token:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        res = await client.post(url, json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}, timeout=5)
        if res.status_code != 200:
            logger.warning(f"⚠️ Telegram Error ({res.status_code}): Verifica TOKEN e CHAT_ID in config.py")
    except Exception as e:
        logger.error(f"Errore invio Telegram: {e}")

async def send_startup_notification():
    mode = "REAL TRADING (SOL)" if Config.REAL_TRADING else "PAPER TRADING (REALISTICO)"
    msg = (
        f"🟢 <b>Zephyr Bot 2.0 Ultra-Realistic!</b>\n\n"
        f"<b>Modalità:</b> {mode}\n"
        f"<b>Budget Iniziale:</b> {virtual_wallet.get_balance():.4f} SOL\n"
        f"<b>Trade Size:</b> {virtual_wallet.trade_amount:.4f} SOL\n"
        f"<b>Slippage Applicato:</b> {Config.SLIPPAGE_BPS / 100}%\n"
        f"<b>Priority Fee / Tx:</b> {Config.ESTIMATED_FEE_SOL} SOL\n"
        f"<b>RPC Auth:</b> Helius Mainnet Connected\n"
        f"<b>Prezzi:</b> DexScreener Live API"
    )
    async with httpx.AsyncClient() as client:
        await send_telegram_msg(client, msg)

async def process_detected_token(token_data: dict):
    token_address = token_data.get("address", "")
    symbol = token_data.get("symbol", "UNKNOWN")
    price_usd = token_data.get("price_usd", 0)

    is_safe, reason = await anti_rug.verify_token_safety(token_address, token_data)
    if not is_safe:
        logger.warning(f"⛔ [RUGPULL EVITATO] ${symbol} scartato -> {reason}")
        return

    trade_info = virtual_wallet.open_virtual_trade(token_address, symbol, price_usd)
    if not trade_info:
        return

    links_html = build_trading_links_text(token_address)
    msg = (
        f"🚀 <b>TRADE APERTO!</b>\n\n"
        f"<b>Token:</b> ${symbol}\n"
        f"<b>Prezzo Ingresso (incl. Slippage):</b> ${trade_info['entry_price_usd']:.8f}\n"
        f"<b>Investiti:</b> {trade_info['buy_sol']} SOL (+{Config.ESTIMATED_FEE_SOL} SOL Fee)\n"
        f"<b>Saldo Libero Rimasto:</b> {virtual_wallet.get_balance():.4f} SOL\n\n"
        f"{links_html}"
    )

    async with httpx.AsyncClient() as client:
        await send_telegram_msg(client, msg)

async def live_pnl_monitor():
    report_counter = 0
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(15)
            report_counter += 1

            open_pos, closed_pos = await virtual_wallet.update_positions_pnl(
                client, 
                take_profit_pct=getattr(Config, "TAKE_PROFIT_PCT", 100.0),
                initial_stop_loss_pct=getattr(Config, "STOP_LOSS_PCT", -30.0)
            )

            for c in closed_pos:
                status = c["status"]
                pnl_usd = c["pnl_sol"] * 135
                
                msg = (
                    f"🎯 <b>TRADE CHIUSO: ${c['symbol']}</b>\n\n"
                    f"<b>Esito:</b> {status}\n"
                    f"<b>PnL Netto (dopo Fees & Slippage):</b> {c['pnl_pct']:+.2f}%\n"
                    f"<b>Guadagno/Perdita Netta:</b> {c['pnl_sol']:+.4f} SOL (~{pnl_usd:+.2f}$)\n"
                    f"<b>Nuovo Saldo Libero:</b> {virtual_wallet.get_balance():.4f} SOL"
                )
                await send_telegram_msg(client, msg)

            if report_counter >= 12 and open_pos:
                report_counter = 0
                total_eq = virtual_wallet.get_total_equity_sol()
                lines = [
                    f"📊 <b>REPORT PORTAFOGLIO REALISTICO</b>",
                    f"<b>Valore Totale Equity:</b> {total_eq:.4f} SOL",
                    f"<b>Saldo Libero:</b> {virtual_wallet.get_balance():.4f} SOL\n"
                ]
                for p in open_pos:
                    lines.append(f"• <b>${p['symbol']}</b>: {p['pnl_pct']:+.2f}% PnL (Max: {p['max_pnl_reached']:+.1f}%)")
                
                report_msg = "\n".join(lines)
                await send_telegram_msg(client, report_msg)

async def main():
    logger.info("🚀 Avvio Zephyr Bot 2.0 (Helius RPC, Slippage, Fees, DexScreener Price API)...")
    await send_startup_notification()

    asyncio.create_task(live_pnl_monitor())
    asyncio.create_task(start_dex_listener(process_detected_token))
    asyncio.create_task(start_twitter_listener(process_detected_token))

    while True:
        await asyncio.sleep(3600)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot arrestato.")
