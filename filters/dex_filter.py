import logging
from config import Config
from dex.onchain import check_solana_mint_security
from dex.rugcheck import check_rug_pull
from dex.risk_analyzer import analyze_token_risk

logger = logging.getLogger(__name__)

async def is_valid_token_async(data: dict) -> tuple[bool, str]:
    """Applica filtri Hermes, controlli On-Chain ed Anti-RugPull."""
    
    # 1. Catena Solana
    if data.get("chainId") != "solana":
        return False, "Chain non supportata"

    # 2. Simbolo pulito
    base_token = data.get("baseToken", {})
    symbol = base_token.get("symbol", "")
    address = base_token.get("address", "")
    
    if len(symbol) > Config.MAX_SYMBOL_LENGTH or not symbol.isalnum():
        return False, "Simbolo non valido o troppo lungo"

    # 3. Market Cap limite
    market_cap = float(data.get("marketCap", 0) or 0)
    if market_cap > Config.MAX_MARKET_CAP:
        return False, f"Market Cap troppo alto (${market_cap:,.0f})"

    # 4. Ratio Buys/Sells (Anti-Dump)
    txns_5m = data.get("txns", {}).get("m5", {})
    buys = int(txns_5m.get("buys", 0) or 0)
    sells = int(txns_5m.get("sells", 0) or 0)

    if sells > buys * 1.3:
        return False, "Pressione di vendita elevata (Dump in corso)"

    # 5. Presenza Links Social
    info = data.get("info", {})
    if not info.get("websites") and not info.get("socials"):
        return False, "Assenza di social/sito web"

    # --- VERIFICA ON-CHAIN RPC & HERMES ANALYZER ---
    if address:
        onchain_res = await check_solana_mint_security(address)
        if not onchain_res["safe"]:
            return False, f"On-Chain Reject: {onchain_res['reason']}"

        rug_report = await check_rug_pull(address)
        
        # Analisi Risk Hermes
        is_safe, risk_reason = analyze_token_risk(data, rug_report, onchain_res)
        if not is_safe:
            return False, f"Hermes Filter Reject: {risk_reason}"

    return True, "Validato"

def calculate_score_and_probability(data: dict) -> tuple[int, int]:
    """Calcola lo score complessivo per la priorità dell'alert."""
    score = 0
    
    liquidity = float(data.get("liquidity", {}).get("usd", 0) or 0)
    info = data.get("info", {})
    txns_5m = data.get("txns", {}).get("m5", {})
    buys = int(txns_5m.get("buys", 0) or 0)
    sells = int(txns_5m.get("sells", 0) or 0)

    if liquidity >= 10000:
        score += 30
    elif liquidity >= 5000:
        score += 20

    if buys + sells > 0 and (buys / (buys + sells)) >= 0.65:
        score += 35

    if info.get("websites"):
        score += 15
    if info.get("socials"):
        score += 20

    probability = min(max(score, 15), 95)
    return score, probability
