import logging
import httpx
from config import Config

logger = logging.getLogger(__name__)


class AntiRugEngine:
    def __init__(self, rpc_url: str = ""):
        self.rpc_url = rpc_url

    async def verify_token_safety(self, token_address: str, dex_data: dict) -> tuple[bool, str]:
        liquidity_usd = float(dex_data.get("liquidity_usd", 0) or 0)
        fdv = float(dex_data.get("fdv", 0) or dex_data.get("market_cap", 0) or 0)
        buys = int(dex_data.get("buys_m5", 0) or 0)
        sells = int(dex_data.get("sells_m5", 0) or 0)
        vol_m5 = float(dex_data.get("volume_m5", 0) or 0)
        score = int(dex_data.get("score", 0) or 0)

        if liquidity_usd < Config.MIN_LIQUIDITY:
            return False, f"Liquidita troppo bassa (${liquidity_usd:,.0f} < ${Config.MIN_LIQUIDITY:,.0f})"

        if fdv > 0 and fdv < Config.MIN_MARKET_CAP:
            return False, f"Market cap troppo basso (${fdv:,.0f})"

        if fdv > Config.MAX_MARKET_CAP:
            return False, f"Market cap troppo alto (${fdv:,.0f})"

        if fdv > 0 and (liquidity_usd / fdv) < 0.10:
            return False, "Ratio liquidita/MC < 10% (sospetto)"

        if buys < Config.MIN_BUYS_M5:
            return False, f"Troppi pochi buy in 5m ({buys} < {Config.MIN_BUYS_M5})"

        if sells > 0 and buys < sells * Config.MIN_BUY_SELL_RATIO:
            return False, f"Pressione vendita (buys {buys} / sells {sells})"

        if vol_m5 < Config.MIN_VOLUME_M5:
            return False, f"Volume 5m basso (${vol_m5:,.0f})"

        if score < Config.MIN_ENTRY_SCORE:
            return False, f"Score troppo basso ({score} < {Config.MIN_ENTRY_SCORE})"

        if buys > 25 and sells == 0:
            return False, "Possibile honeypot (0 sell con tanti buy)"

        if self.rpc_url:
            ok, reason = await self._check_onchain_authorities(token_address)
            if not ok:
                return False, reason

        return True, "SAFE"

    async def _check_onchain_authorities(self, token_address: str) -> tuple[bool, str]:
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "getAccountInfo",
            "params": [token_address, {"encoding": "jsonParsed"}],
        }
        try:
            async with httpx.AsyncClient(timeout=4.0) as client:
                res = await client.post(self.rpc_url, json=payload)
                if res.status_code != 200:
                    return True, "OK"
                data = res.json()
                parsed = (
                    data.get("result", {})
                    .get("value", {})
                    .get("data", {})
                    .get("parsed", {})
                    .get("info", {})
                )
                if parsed.get("mintAuthority") is not None:
                    return False, "Mint Authority attiva"
                if parsed.get("freezeAuthority") is not None:
                    return False, "Freeze Authority attiva"
        except Exception as e:
            logger.error(f"Errore RPC Helius: {e}")
        return True, "OK"
