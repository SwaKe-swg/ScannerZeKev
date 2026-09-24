import asyncio
import time
import logging
import httpx

from config import Config
from anti_rug_engine import AntiRugEngine
from risk_manager import PositionManager
from filters.blacklist import add_blacklist, is_blacklisted

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
last_entry_ts = 0.0

virtual_wallet = PositionManager(
    initial_balance=START_BUDGET,
    trade_amount=getattr(Config, "TRADE_AMOUNT_SOL", 0.015),
)


def _pnl_word(pct: float) -> str:
    if pct > 0.5:
        return "in guadagno"
    if pct < -0.5:
        return "in perdita"
    return "quasi in pari"


def _loss_lesson(c: dict) -> str:
    status = (c.get("status") or "").upper()
    peak = float(c.get("max_pnl_reached") or 0)
    pct = float(c.get("pnl_pct") or 0)
    if "STOP LOSS" in status:
        if peak < 3:
            return (
                "Lezione: entrato gia in fase debole (mai andato davvero in plus). "
                "Da ora evitiamo token in calo nei 5 min e quelli gia stoppati."
            )
        return (
            f"Lezione: era salito fino a {peak:+.1f}% poi ha dumpato a {pct:+.1f}%. "
            "Trailing piu stretto e blacklist dopo lo stop."
        )
    if "TRAILING" in status:
        return "Trailing ha chiuso per proteggere: meglio un piccolo plus/minus che un crollo."
    return "Chiusura automatica secondo le regole."


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
        "REALE (SOL veri)"
        if Config.REAL_TRADING
        else "PAPER (solo simulazione)"
    )
    tp = getattr(Config, "TAKE_PROFIT_PCT", 35.0)
    sl = getattr(Config, "STOP_LOSS_PCT", -15.0)
    lines = [
        "🚀 <b>Zephyr Bot 2.2</b>",
        "",
        f"🎛️ <b>Modalita:</b> {mode}",
        f"💰 <b>Budget:</b> {START_BUDGET:.4f} SOL",
        (
            f"🎯 <b>Ingresso:</b> {virtual_wallet.trade_amount:.4f} SOL "
            f"(max {getattr(Config, 'MAX_OPEN_POSITIONS', 2)} aperti)"
        ),
        f"⏱️ <b>Cooldownoldown:</b> {getattr(Config, 'COOLDOWN_SECONDS', 90)}s",
        "",
        "✅ <b>Entra solo se:</b>",
        f"• liquidita ≥ ${getattr(Config, 'MIN_LIQUIDITY', 12000):,.0f}",
        (
            f"• market cap ${getattr(Config, 'MIN_MARKET_CAP', 20000):,.0f}"
            f"–${getattr(Config, 'MAX_MARKET_CAP', 250000):,.0f}"
        ),
        f"• prezzo in salita ≥ +{getattr(Config, 'MIN_PRICE_CHANGE_M5', 2.0):.0f}% (5m)",
        f"• score ≥ {getattr(Config, 'MIN_ENTRY_SCORE', 70)} + buy pressure",
        "• niente blacklist (token gia stoppati)",
        "",
        f"🚪 <b>Uscite:</b> TP +{tp:.0f}% | SL {sl:.0f}% | trailing da +6%",
        "",
        "🧠 <i>Lezione $WIRE: tanti buy con prezzo gia in calo = trappola. "
        "Ora rifiutiamo i falling knife.</i>",
    ]
    async with httpx.AsyncClient() as client:
        await send_telegram_msg(client, chr(10).join(lines))


async def process_detected_token(token_data: dict):
    token_address = token_data.get("address", "")
    symbol = token_data.get("symbol", "UNKNOWN")
    price_usd = token_data.get("price_usd", 0)

    bl, why = is_blacklisted(token_address, symbol)
    if bl:
        logger.info(f"Blacklist skip ${symbol} ({why})")
        return

    is_safe, reason = await anti_rug.verify_token_safety(token_address, token_data)
    if not is_safe:
        logger.warning(f"[SKIP] ${symbol} -> {reason}")
        return

    global last_entry_ts
    now = time.time()
    cooldown = float(getattr(Config, "COOLDOWN_SECONDS", 90))
    if now - last_entry_ts < cooldown:
        logger.info(f"Cooldownoldown attivo, skip ${symbol}")
        return

    trade_info = virtual_wallet.open_virtual_trade(token_address, symbol, price_usd)
    if not trade_info:
        return

    last_entry_ts = now
    chg = token_data.get("price_change_m5", 0)
    score = token_data.get("score", 0)
    links_html = build_trading_links_text(token_address)
    lines = [
        "🟢 <b>Nuova posizione PAPER</b>",
        "",
        f"🪙 <b>Token:</b> ${symbol}",
        f"📥 <b>Ingresso:</b> ${trade_info['entry_price_usd']:.8f}",
        f"💵 <b>Investiti:</b> {trade_info['buy_sol']} SOL (+{Config.ESTIMATED_FEE_SOL} fee)",
        f"🏦 <b>Liberi:</b> {virtual_wallet.get_balance():.4f} SOL",
        f"📊 <b>Score:</b> {score} | momentum 5m: {chg:+.1f}%",
        "",
        "⏳ Non e ancora un guadagno: conta solo a chiusura TP/SL.",
        "",
        links_html,
    ]
    async with httpx.AsyncClient() as client:
        await send_telegram_msg(client, chr(10).join(lines))


async def live_pnl_monitor():
    report_counter = 0
    async with httpx.AsyncClient() as client:
        while True:
            await asyncio.sleep(8)
            report_counter += 1

            open_pos, closed_pos = await virtual_wallet.update_positions_pnl(
                client,
                take_profit_pct=getattr(Config, "TAKE_PROFIT_PCT", 35.0),
                initial_stop_loss_pct=getattr(Config, "STOP_LOSS_PCT", -15.0),
            )

            for c in closed_pos:
                status = c["status"]
                pnl_usd = c["pnl_sol"] * 135
                buy = c.get("buy_sol", 0.0)
                won = c["pnl_sol"] >= 0
                addr = c.get("address") or c.get("token_address") or ""
                # positions may store key differently — risk_manager uses positions dict by addr
                if not won:
                    # find address from positions was removed; use symbol blacklist at least
                    add_blacklist(addr, c.get("symbol", ""), reason=status)

                if won:
                    titolo = "🟢 <b>Chiusura in GUADAGNO</b> (paper)"
                    plain = (
                        f"✅ Hai messo in tasca {c['pnl_sol']:+.4f} SOL "
                        f"(circa {pnl_usd:+.2f} $) su {buy:.4f} SOL."
                    )
                else:
                    titolo = "🔴 <b>Chiusura in PERDITA</b> (paper)"
                    plain = (
                        f"❌ Hai perso {abs(c['pnl_sol']):.4f} SOL "
                        f"(circa {abs(pnl_usd):.2f} $) su {buy:.4f} SOL. "
                        f"Soldi veri: zero (simulazione)."
                    )
                    # blacklist by scanning - open_virtual stores address as key; copy onto pos
                lesson = _loss_lesson(c)
                lines = [
                    titolo,
                    f"🪙 Token: <b>${c['symbol']}</b>",
                    "",
                    plain,
                    "",
                    f"📌 <b>Perche ha chiuso:</b> {status}",
                    f"📉 <b>Variazione:</b> {c['pnl_pct']:+.2f}% (dopo fee/slippage)",
                    f"🏔️ <b>Picco visto:</b> {c.get('max_pnl_reached', 0):+.1f}%",
                    f"🏦 <b>Liberi ora:</b> {virtual_wallet.get_balance():.4f} SOL",
                    "",
                    f"🧠 <b>Cosa impariamo:</b> {lesson}",
                    "",
                    "<i>Regole 2.2: no falling knife, blacklist post-SL, score≥70, emoji on.</i>",
                ]
                await send_telegram_msg(client, chr(10).join(lines))

            if report_counter >= 15 and open_pos:
                report_counter = 0
                total_eq = virtual_wallet.get_total_equity_sol()
                free = virtual_wallet.get_balance()
                in_pos = total_eq - free
                vs_start = total_eq - START_BUDGET
                vs_start_pct = (vs_start / START_BUDGET) * 100.0 if START_BUDGET else 0.0
                lines = [
                    "📊 <b>Report portafoglio PAPER</b>",
                    "",
                    f"💼 <b>Totale stimato:</b> {total_eq:.4f} SOL",
                    f"💵 <b>Liberi:</b> {free:.4f} SOL",
                    f"📂 <b>Nelle posizioni:</b> {in_pos:.4f} SOL",
                    f"📈 <b>Vs inizio:</b> {vs_start:+.4f} SOL ({vs_start_pct:+.1f}%)",
                    "",
                    "📋 <b>Aperti:</b>",
                ]
                for p in open_pos:
                    pct = p["pnl_pct"]
                    peak = p["max_pnl_reached"]
                    emoji = "🟢" if pct >= 0 else "🔴"
                    lines.append(
                        f"{emoji} <b>${p['symbol']}</b> ora {pct:+.2f}% "
                        f"({_pnl_word(pct)}) | picco {peak:+.1f}%"
                    )
                lines.extend(
                    [
                        "",
                        "<i>Il guadagno conta solo a chiusura TP/trailing.</i>",
                    ]
                )
                await send_telegram_msg(client, chr(10).join(lines))


async def main():
    logger.info("Avvio Zephyr Bot 2.2...")
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
