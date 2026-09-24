from config import Config


def pair_metrics(main_pair: dict) -> dict:
    txns = (main_pair.get("txns") or {}).get("m5") or {}
    vol = (main_pair.get("volume") or {})
    liq = (main_pair.get("liquidity") or {})
    info = main_pair.get("info") or {}
    return {
        "symbol": (main_pair.get("baseToken") or {}).get("symbol", "TOKEN"),
        "address": (main_pair.get("baseToken") or {}).get("address", ""),
        "price_usd": float(main_pair.get("priceUsd") or 0),
        "liquidity_usd": float(liq.get("usd") or 0),
        "fdv": float(main_pair.get("fdv") or main_pair.get("marketCap") or 0),
        "market_cap": float(main_pair.get("marketCap") or main_pair.get("fdv") or 0),
        "buys_m5": int(txns.get("buys") or 0),
        "sells_m5": int(txns.get("sells") or 0),
        "volume_m5": float(vol.get("m5") or 0),
        "has_socials": bool(info.get("websites") or info.get("socials")),
        "dex_id": main_pair.get("dexId", ""),
    }


def score_pair(m: dict) -> int:
    score = 0
    liq = m["liquidity_usd"]
    buys = m["buys_m5"]
    sells = m["sells_m5"]
    vol = m["volume_m5"]

    if liq >= 50000:
        score += 35
    elif liq >= 25000:
        score += 28
    elif liq >= 12000:
        score += 18

    total = buys + sells
    if total > 0 and buys / total >= 0.65:
        score += 30
    elif total > 0 and buys / total >= 0.55:
        score += 15

    if buys >= 20:
        score += 15
    elif buys >= 8:
        score += 8

    if vol >= 10000:
        score += 15
    elif vol >= 2000:
        score += 8

    if m["has_socials"]:
        score += 10

    # Prefer Raydium/Orca style pools over pure pump spam if present
    if m["dex_id"] in ("raydium", "orca", "meteora"):
        score += 5

    return min(score, 100)


def hard_reject(m: dict) -> tuple[bool, str]:
    if m["liquidity_usd"] < Config.MIN_LIQUIDITY:
        return True, "liq"
    if m["market_cap"] and m["market_cap"] > Config.MAX_MARKET_CAP:
        return True, "mc_high"
    if m["market_cap"] and m["market_cap"] < Config.MIN_MARKET_CAP:
        return True, "mc_low"
    if m["buys_m5"] < Config.MIN_BUYS_M5:
        return True, "buys"
    if m["volume_m5"] < Config.MIN_VOLUME_M5:
        return True, "vol"
    if m["sells_m5"] > 0 and m["buys_m5"] < m["sells_m5"] * Config.MIN_BUY_SELL_RATIO:
        return True, "sell_pressure"
    if Config.REQUIRE_SOCIALS and not m["has_socials"]:
        return True, "socials"
    sym = m["symbol"] or ""
    if len(sym) > Config.MAX_SYMBOL_LENGTH or not sym.replace(" ", "").isalnum():
        return True, "symbol"
    return False, ""
