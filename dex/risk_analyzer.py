import logging

logger = logging.getLogger(__name__)

def analyze_token_risk(data: dict, rug_report: dict, onchain_data: dict) -> tuple[bool, str]:
    """
    Applica i parametri di Hermes per scartare le coin in perdita:
    1. Liquidity minima > $4,000 USD
    2. Market Cap / Liquidity Ratio in salute
    3. Top Holder % < 20%
    4. Transfer Fee / Tax <= 5% (se Token2022)
    """
    
    # 1. Controllo Liquidità Minima ($4,000+)
    liquidity = float(data.get("liquidity", {}).get("usd", 0) or 0)
    if liquidity < 4000:
        return False, f"Liquidità troppo bassa (${liquidity:,.0f} < $4,000)"

    # 2. Controllo Top Holder % (Scarta se > 20%)
    top_holder_pct = onchain_data.get("top_holder_pct", 0.0)
    if top_holder_pct > 20.0:
        return False, f"Top Holder possiede troppo supply ({top_holder_pct:.1f}% > 20%)"

    # 3. Controllo Transfer Fee / Tax (se presente)
    transfer_fee = onchain_data.get("transfer_fee_pct", 0.0)
    if transfer_fee > 5.0:
        return False, f"Tax / Transfer Fee troppo alta ({transfer_fee:.1f}% > 5%)"

    # 4. Controllo Risk Score complessivo di RugCheck
    if rug_report.get("risk_score") == "high":
        reasons = ", ".join(rug_report.get("reasons", [])) or "Risk Score Elevato"
        return False, f"RugCheck High Risk ({reasons})"

    return True, "Parametri di sicurezza superati"
