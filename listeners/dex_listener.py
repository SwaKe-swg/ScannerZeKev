import asyncio
import logging
import httpx

from filters.entry_score import hard_reject, pair_metrics, score_pair
from config import Config

logger = logging.getLogger(__name__)


async def start_dex_listener(callback):
    logger.info(
        "DEX Listener avviato (filtri hard + score >= %s, liq >= %s)...",
        Config.MIN_ENTRY_SCORE,
        Config.MIN_LIQUIDITY,
    )
    seen_tokens = set()
    rejected = 0
    accepted = 0

    while True:
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                while True:
                    try:
                        url = "https://api.dexscreener.com/token-profiles/latest/v1"
                        res = await client.get(url)

                        if res.status_code == 200:
                            data = res.json()
                            for item in data:
                                if item.get("chainId") != "solana":
                                    continue
                                token_address = item.get("tokenAddress")
                                if not token_address or token_address in seen_tokens:
                                    continue
                                seen_tokens.add(token_address)
                                if len(seen_tokens) > 2000:
                                    seen_tokens.pop()

                                pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                                pair_res = await client.get(pair_url)
                                if pair_res.status_code != 200:
                                    continue
                                pairs = pair_res.json().get("pairs") or []
                                if not pairs:
                                    continue

                                main_pair = pairs[0]
                                m = pair_metrics(main_pair)
                                m["address"] = token_address
                                rej, why = hard_reject(m)
                                if rej:
                                    rejected += 1
                                    continue

                                sc = score_pair(m)
                                m["score"] = sc
                                if sc < Config.MIN_ENTRY_SCORE:
                                    rejected += 1
                                    logger.info(
                                        "Skip $%s score=%s (%s)",
                                        m["symbol"],
                                        sc,
                                        why or "score",
                                    )
                                    continue

                                accepted += 1
                                token_info = {
                                    "address": token_address,
                                    "symbol": m["symbol"],
                                    "source": f"DexScreener ({m['dex_id']})",
                                    "price_usd": m["price_usd"],
                                    "liquidity_usd": m["liquidity_usd"],
                                    "fdv": m["fdv"],
                                    "market_cap": m["market_cap"],
                                    "buys_m5": m["buys_m5"],
                                    "sells_m5": m["sells_m5"],
                                    "volume_m5": m["volume_m5"],
                                    "score": sc,
                                    "holders": [],
                                    "trades": [],
                                }
                                logger.info(
                                    "Candidato $%s score=%s liq=$%s buys5m=%s",
                                    m["symbol"],
                                    sc,
                                    int(m["liquidity_usd"]),
                                    m["buys_m5"],
                                )
                                await callback(token_info)

                        elif res.status_code == 429:
                            await asyncio.sleep(20)

                    except Exception as e:
                        logger.error("Errore scanner: %s", e)

                    if (rejected + accepted) and (rejected + accepted) % 20 == 0:
                        logger.info(
                            "Filtro: accepted=%s rejected=%s (reject ratio alto = meglio)",
                            accepted,
                            rejected,
                        )
                    await asyncio.sleep(10)

        except Exception:
            await asyncio.sleep(5)
