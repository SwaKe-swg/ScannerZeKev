import aiohttp
import logging

logger = logging.getLogger(__name__)

async def check_rug_pull(mint_address: str) -> dict:
    """
    Interroga RugCheck.xyz API e restituisce un dizionario strutturato con lo stato di rischio del token.
    """
    url = f"https://api.rugcheck.xyz/v1/tokens/{mint_address}/report/summary"
    
    default_result = {
        "is_honeypot": False,
        "is_renounced": True,
        "lp_locked": "unknown",
        "top_holder_pct": 0.0,
        "risk_score": "low",
        "raw_score": 0,
        "reasons": []
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, timeout=5) as resp:
                if resp.status != 200:
                    logger.warning(f"RugCheck non ha ancora indicizzato {mint_address} (Status {resp.status})")
                    return default_result

                data = await resp.json()
                score = data.get("score", 0)
                risks = data.get("risks", [])

                danger_reasons = []
                is_honeypot = False
                is_renounced = True
                lp_locked = "no"

                for risk in risks:
                    level = risk.get("level", "").lower()
                    name = risk.get("name", "")
                    description = risk.get("description", "")

                    # Rilevamento Freeze / Mint / Honeypot
                    if "freeze" in name.lower() or "honeypot" in name.lower() or "transfer fee" in name.lower():
                        is_honeypot = True

                    if "mint" in name.lower() and "single owner" in description.lower():
                        is_renounced = False

                    if "lp" in name.lower() and ("locked" in description.lower() or "burned" in description.lower()):
                        lp_locked = "yes"

                    if level in ["danger", "critical"]:
                        danger_reasons.append(name)

                # Determina il Risk Score complessivo
                if score >= 1500 or is_honeypot or len(danger_reasons) > 0:
                    risk_level = "high"
                elif score >= 500:
                    risk_level = "medium"
                else:
                    risk_level = "low"

                return {
                    "is_honeypot": is_honeypot,
                    "is_renounced": is_renounced,
                    "lp_locked": lp_locked,
                    "top_holder_pct": 0.0,  # Gestito On-Chain RPC
                    "risk_score": risk_level,
                    "raw_score": score,
                    "reasons": danger_reasons
                }

    except Exception as e:
        logger.error(f"Errore durante il controllo RugCheck per {mint_address}: {e}")
        return default_result
