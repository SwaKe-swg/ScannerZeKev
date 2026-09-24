from config import Config


def pair_metrics(main_pair: dict) -> dict:
    txns = (main_pair.get("txns") or {}).get("m5") or {}
    vol = (main_pair.get("volume") or {})
    liq = (main_pair.get("liquidity") or {})
    info = main_pair.get("info") or {}
    pc = main_pair.get("priceChange") or {}
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
        "price_change_m5": float(pc.get("m5") or 0),
        "price_change_h1": float(pc.get("h1") or 0),
        "has_socials": bool(info.get("websites") or info.get("socials")),
        "dex_id": main_pair.get("dexId", ""),
    }


def score_pair(m: dict) -> int:
    score = 0
    liq = m["liquidity_usd"]
    buys = m["buys_m5"]
    sells = m["sells_m5"]
    vol = m["volume_m5"]
    chg = m["price_change_m5"]

    if liq >= 50000:
        score += 30
    elif liq >= 25000:
        score += 24
    elif liq >= 12000:
        score += 14

    total = buys + sells
    if total > 0 and buys / total >= 0.65:
        score += 22
    elif total > 0 and buys / total >= 0.55:
        score += 10

    # Momentum: reward rising price, punish dumps
    if chg >= 15:
        score += 25
    elif chg >= 5:
        score += 18
    elif chg >= 3:
        score += 10
    elif chg < 0:
        score -= 25

    # Too many buys with flat/down price = late to the party
    if buys >= 100 and chg < 5:
        score -= 20

    if 8 <= buys <= 60:
        score += 12
    elif buys > 150:
        score -= 8

    if vol >= 10000:
        score += 12
    elif vol >= 2000:
        score += 6

    if m["has_socials"]:
        score += 8

    if m["dex_id"] in ("raydium", "orca", "meteora"):
        score += 5

    return max(0, min(score, 100))


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
    # Falling knife: WIRE lesson — high activity while dumping
    min_chg = float(getattr(Config, "MIN_PRICE_CHANGE_M5", 3.0))
    max_chg = float(getattr(Config, "MAX_PRICE_CHANGE_M5", 80.0))
    if m["price_change_m5"] < min_chg:
        return True, f"momentum_down({m['price_change_m5']:+.1f}%)"
    if m["price_change_m5"] > max_chg:
        return True, f"already_pumped({m['price_change_m5']:+.1f}%)"
    if m["buys_m5"] >= 100 and m["price_change_m5"] < 8:
        return True, "late_chase"
    if Config.REQUIRE_SOCIALS and not m["has_socials"]:
        return True, "socials"
    sym = m["symbol"] or ""
    if len(sym) > Config.MAX_SYMBOL_LENGTH or not sym.replace(" ", "").isalnum():
        return True, "symbol"
    return False, ""
