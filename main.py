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
        return (
            f'Link: <a href="https://dexscreener.com/solana/{token_address}">DexScreener</a>'
        )

from listeners.dex_listener import start_dex_listener
from listeners.twitter_listener import start_twitter_listener

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

helius_url = getattr(Config, "HELIUS_RPC_URL", "")
anti_rug = AntiRugEngine(rpc_url=helius_url)

START_BUDGET = float(getattr(Config, "VIRTUAL_SOL_BALANCE", 0.30))
virtual_wallet = PositionManager(
    initial_balance=START_BUDGET,
    trade_amount=getattr(Config, "TRADE_AMOUNT_SOL", 0.03),
)


def _pnl_word(pct: float) -> str:
    if pct > 0.5:
        return "in guadagno"
    if pct < -0.5:
        return "in perdita"
    return "quasi in pari"


async def send_telegram_msg(client: httpx.AsyncClient, text: str):
    token = getattr(Config, "TELEGRAM_BOT_TOKEN", "")
    chat_id = getattr(Config, "TELEGRAM_CHAT_ID", "")
    if not token or "IL_TUO" in token:
        return
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        res = await client.post(
            url,
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=5,
        )
        if res.status_code != 200:
            logger.warning(
                f"Telegram Error ({res.status_code}): verifica TOKEN e CHAT_ID"
            )
    except Exception as e:
        logger.error(f"Errore invio Telegram: {e}")


async def send_startup_notification():
    mode = (
        "REALE (usa SOL veri)"
        if Config.REAL_TRADING
        else "PAPER (simulazione, niente SOL veri)"
    )
    tp = getattr(Config, "TAKE_PROFIT_PCT", 100.0)
    sl = getattr(Config, "STOP_LOSS_PCT", -30.0)
    msg = (
        f"<b>Zephyr Bot 2.0 avviato</b>\n\n"
        f"<b>Modalita:</b> {mode}\n"
        f"<b>Budget di partenza:</b> {START_BUDGET:.4f} SOL "
        f"(soldi virtuali con cui inizia)\n"
        f"<b>Ogni ingresso:</b> {virtual_wallet.trade_amount:.4f} SOL "
        f"(+{Config.ESTIMATED_FEE_SOL} SOL di fee stimate)\n"
        f"<b>Slippage stimato:</b> {Config.SLIPPAGE_BPS / 100}% "
        f"(peggioramento prezzo all'ingresso/uscita)\n\n"
        f"<b>Quando chiude da solo:</b>\n"
        f"• Take profit a <b>+{tp:.0f}%</b> (raddoppio → chiude in guadagno)\n"
        f"• Stop loss a <b>{sl:.0f}%</b> (taglia la perdita)\n"
        f"• Trailing stop se prima era salito molto "
        f"(protegge parte del guadagno)\n\n"
        f"Ogni ~3 minuti arriva un report sul portafoglio."
    )
    async with httpx.AsyncClient() as client:
        await send_telegram_msg(client, msg)


async def process_detected_token(token_data: dict):
    token_address = token_data.get("address", "")
    symbol = token_data.get("symbol", "UNKNOWN")
    price_usd = token_data.get("price_usd", 0)

    is_safe, reason = await anti_rug.verify_token_safety(token_address, token_data)
    if not is_safe:
        logger.warning(f"[RUGPULL EVITATO] ${symbol} scartato -> {reason}")
        return

    trade_info = virtual_wallet.open_virtual_trade(token_address, symbol, price_usd)
    if not trade_info:
        return

    links_html = build_trading_links_text(token_address)
    msg = (
        f"<b>Nuova posizione PAPER aperta</b>\n\n"
        f"<b>Token:</b> ${symbol}\n"
        f"<b>Prezzo di ingresso (con slippage):</b> "
        f"${trade_info['entry_price_usd']:.8f}\n"
        f"<b>Quanto hai messo:</b> {trade_info['buy_sol']} SOL "
        f"(+{Config.ESTIMATED_FEE_SOL} SOL fee)\n"
        f"<b>Soldi ancora liberi:</b> {virtual_wallet.get_balance():.4f} SOL "
        f"(non investiti, pronti per altri ingressi)\n\n"
        f"Questa non e ancora un guadagno: conta solo quando arriva "
        f"<b>TRADE CHIUSO</b> in take profit / stop.\n\n"
        f"{links_html}"
    )

    async with httpx.AsyncClient() as client:
        await send_telegram_msg(client, msg)


async def live_pnl_monitor():
    report_counter = 0
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(8)
            report_counter += 1

            open_pos, closed_pos = await virtual_wallet.update_positions_pnl(
                client,
                take_profit_pct=getattr(Config, "TAKE_PROFIT_PCT", 100.0),
                initial_stop_loss_pct=getattr(Config, "STOP_LOSS_PCT", -30.0),
            )

            for c in closed_pos:
                status = c["status"]
                pnl_usd = c["pnl_sol"] * 135
                buy = c.get("buy_sol", 0.0)
                won = c["pnl_sol"] >= 0
                if won:
                    titolo = "Chiusura in guadagno (paper)"
                    plain = (
                        "Hai recuperato il capitale investito e in piu "
                        + f"{c['pnl_sol']:+.4f} SOL (circa {pnl_usd:+.2f} $)."
                    )
                else:
                    titolo = "Chiusura in perdita (paper)"
                    plain = (
                        f"Hai perso {abs(c['pnl_sol']):.4f} SOL "
                        + f"(circa {abs(pnl_usd):.2f} $) su {buy:.4f} SOL investiti. "
                        + "Niente soldi veri: e solo simulazione."
                    )
                lines = [
                    f"<b>{titolo}</b>",
                    f"Token: <b>${c['symbol']}</b>",
                    "",
                    plain,
                    "",
                    f"<b>Perche ha chiuso:</b> {status}",
                    f"<b>Variazione prezzo:</b> {c['pnl_pct']:+.2f}% (gia tolte fee e slippage)",
                    f"<b>Soldi liberi ora:</b> {virtual_wallet.get_balance():.4f} SOL",
                    "",
                    "<i>Regole attuali: stop loss -12%, take profit +50%, trailing se era salito; ogni ingresso 0.02 SOL.</i>",
                ]
                msg = chr(10).join(lines)
                await send_telegram_msg(client, msg)

            if report_counter >= 15 and open_pos:
                report_counter = 0
                total_eq = virtual_wallet.get_total_equity_sol()
                free = virtual_wallet.get_balance()
                in_pos = total_eq - free
                vs_start = total_eq - START_BUDGET
                vs_start_pct = (vs_start / START_BUDGET) * 100.0 if START_BUDGET else 0.0

                lines = [
                    "<b>Report portafoglio PAPER</b> (ogni ~2 min)",
                    "",
                    f"<b>Totale stimato ora:</b> {total_eq:.4f} SOL",
                    "  = soldi liberi + valore attuale delle posizioni aperte",
                    f"<b>Soldi liberi:</b> {free:.4f} SOL (non investiti)",
                    f"<b>Nelle posizioni:</b> {in_pos:.4f} SOL (ancora aperti)",
                    (
                        f"<b>Vs budget iniziale ({START_BUDGET:.2f} SOL):</b> "
                        f"{vs_start:+.4f} SOL ({vs_start_pct:+.1f}%)"
                    ),
                    "",
                    "<b>Posizioni aperte</b> (non ancora chiuse):",
                ]
                for p in open_pos:
                    pct = p["pnl_pct"]
                    peak = p["max_pnl_reached"]
                    word = _pnl_word(pct)
                    lines.append(
                        f"• <b>${p['symbol']}</b> — ora {pct:+.2f}% ({word})"
                    )
                    lines.append(
                        f"   Picco visto finora: {peak:+.1f}% "
                        f"(massimo guadagno toccato senza aver chiuso)"
                    )
                lines.extend(
                    [
                        "",
                        "<i>PnL% = quanto sei sopra/sotto il prezzo di ingresso.</i>",
                        "<i>Il guadagno conta davvero solo a TRADE CHIUSO "
                        "(TP +100%, SL -30% o trailing).</i>",
                    ]
                )
                await send_telegram_msg(client, "\n".join(lines))


async def main():
    logger.info(
        "Avvio Zephyr Bot 2.0 (Helius RPC, Slippage, Fees, DexScreener Price API)..."
    )
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
