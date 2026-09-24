import logging
import httpx

logger = logging.getLogger(__name__)

class AntiRugEngine:
    def __init__(self, rpc_url: str = ""):
        self.rpc_url = rpc_url

    async def verify_token_safety(self, token_address: str, dex_data: dict) -> tuple[bool, str]:
        liquidity_usd = dex_data.get("liquidity_usd", 0)
        fdv = dex_data.get("fdv", 0)
        
        if liquidity_usd < 8000:
            return False, f"Liquidità troppo bassa (${liquidity_usd:,.0f} < $8,000)"
        
        if fdv > 0 and fdv < 15000:
            return False, f"Market Cap (FDV) troppo basso (${fdv:,.0f} < $15,000)"

        if fdv > 0 and (liquidity_usd / fdv) < 0.08:
            return False, "Ratio Liquidità/MC sospetto (Meno dell'8%)"

        if self.rpc_url:
            has_authority, auth_reason = await self._check_onchain_authorities(token_address)
            if not has_authority:
                return False, auth_reason

        is_safe_distribution, dist_reason = await self._check_holder_distribution(token_address)
        if not is_safe_distribution:
            return False, dist_reason

        return True, "SAFE"

    async def _check_onchain_authorities(self, token_address: str) -> tuple[bool, str]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [token_address, {"encoding": "jsonParsed"}]
        }
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(self.rpc_url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    parsed_info = data.get("result", {}).get("value", {}).get("data", {}).get("parsed", {}).get("info", {})
                    
                    if parsed_info.get("mintAuthority") is not None:
                        return False, "Mint Authority ATTIVA (Rischio inflazione)"
                    
                    if parsed_info.get("freezeAuthority") is not None:
                        return False, "Freeze Authority ATTIVA (Rischio blocco wallet)"
        except Exception as e:
            logger.error(f"Errore RPC Helius: {e}")
        return True, "OK"

    async def _check_holder_distribution(self, token_address: str) -> tuple[bool, str]:
        try:
            url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    pairs = data.get("pairs")
                    if pairs:
                        txns = pairs[0].get("txns", {}).get("m5", {})
                        buys = txns.get("buys", 0)
                        sells = txns.get("sells", 0)

                        if buys > 20 and sells == 0:
                            return False, "HONEYPOT RILEVATO (0 vendite)"
                        
                        if buys > 10 and (sells / buys) < 0.05:
                            return False, "RAPPORTO SELL/BUY SOSPETTO (<5% vendite)"
        except Exception as e:
            logger.error(f"Errore distribution: {e}")

        return True, "OK"
