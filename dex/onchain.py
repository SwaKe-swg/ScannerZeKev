import aiohttp
import logging
from config import Config

logger = logging.getLogger(__name__)

async def check_solana_mint_security(mint_address: str) -> dict:
    default_res = {
        "safe": True,
        "reason": "OK",
        "top_holder_pct": 0.0,
        "transfer_fee_pct": 0.0
    }

    if not Config.HELIUS_API_KEY:
        return default_res

    payload = {
        "jsonrpc": "2.0",
        "id": "zephyr-check",
        "method": "getAccountInfo",
        "params": [mint_address, {"encoding": "jsonParsed"}]
    }

    try:
        async with aiohttp.ClientSession() as session:
            # 1. Verifica Account Info (Mint & Freeze Authority)
            async with session.post(Config.HELIUS_RPC_URL, json=payload) as resp:
                if resp.status != 200:
                    return {"safe": False, "reason": f"RPC Status {resp.status}", "top_holder_pct": 0.0, "transfer_fee_pct": 0.0}
                
                result = await resp.json()
                value = result.get("result", {}).get("value")
                if not value:
                    return {"safe": False, "reason": "Token non trovato on-chain", "top_holder_pct": 0.0, "transfer_fee_pct": 0.0}

                parsed_info = value.get("data", {}).get("parsed", {}).get("info", {})
                
                if Config.CHECK_MINT_AUTHORITY and parsed_info.get("mintAuthority") is not None:
                    return {"safe": False, "reason": "Mint Authority attiva", "top_holder_pct": 0.0, "transfer_fee_pct": 0.0}

                if Config.CHECK_FREEZE_AUTHORITY and parsed_info.get("freezeAuthority") is not None:
                    return {"safe": False, "reason": "Freeze Authority attiva", "top_holder_pct": 0.0, "transfer_fee_pct": 0.0}

                # Controllo Transfer Fee (Token2022 Tax)
                extensions = parsed_info.get("extensions", [])
                transfer_fee_pct = 0.0
                for ext in extensions:
                    if ext.get("extension") == "transferFeeConfig":
                        fee_config = ext.get("state", {}).get("newerTransferFee", {})
                        bps = fee_config.get("maximumFee", 0)
                        transfer_fee_pct = (bps / 10000) * 100

            # 2. Verifica Top Holder Percentage
            holders_payload = {
                "jsonrpc": "2.0",
                "id": "zephyr-holders",
                "method": "getTokenLargestAccounts",
                "params": [mint_address]
            }
            top_holder_pct = 0.0
            async with session.post(Config.HELIUS_RPC_URL, json=holders_payload) as resp:
                if resp.status == 200:
                    h_result = await resp.json()
                    accounts = h_result.get("result", {}).get("value", [])
                    if accounts:
                        supply_payload = {
                            "jsonrpc": "2.0",
                            "id": "zephyr-supply",
                            "method": "getTokenSupply",
                            "params": [mint_address]
                        }
                        async with session.post(Config.HELIUS_RPC_URL, json=supply_payload) as s_resp:
                            if s_resp.status == 200:
                                s_data = await s_resp.json()
                                total_supply = float(s_data.get("result", {}).get("value", {}).get("uiAmount", 0) or 0)
                                if total_supply > 0:
                                    top_holder_amount = float(accounts[0].get("uiAmount", 0) or 0)
                                    top_holder_pct = (top_holder_amount / total_supply) * 100

        return {
            "safe": True,
            "reason": "Controlli superati",
            "top_holder_pct": top_holder_pct,
            "transfer_fee_pct": transfer_fee_pct
        }

    except Exception as e:
        logger.warning(f"Errore controllo On-Chain per {mint_address}: {e}")
        return default_res
