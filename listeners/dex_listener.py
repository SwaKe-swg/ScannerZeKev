import asyncio
import logging
import httpx

logger = logging.getLogger(__name__)

async def start_dex_listener(callback):
    """Scansiona i token e invia il prezzo d'ingresso in USD."""
    logger.info("📡 DEX Listener avviato (Filtro Liquidità + Tracciamento Prezzo)...")
    seen_tokens = set()
    
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
                                if item.get("chainId") == "solana":
                                    token_address = item.get("tokenAddress")
                                    if token_address and token_address not in seen_tokens:
                                        seen_tokens.add(token_address)
                                        if len(seen_tokens) > 1000:
                                            seen_tokens.pop()

                                        pair_url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
                                        pair_res = await client.get(pair_url)
                                        
                                        if pair_res.status_code == 200:
                                            pair_data = pair_res.json()
                                            pairs = pair_data.get("pairs")
                                            
                                            if pairs:
                                                main_pair = pairs[0]
                                                liquidity_usd = main_pair.get("liquidity", {}).get("usd", 0)
                                                price_usd = float(main_pair.get("priceUsd", 0))

                                                if liquidity_usd < 5000:
                                                    continue

                                                token_info = {
                                                    "address": token_address,
                                                    "symbol": main_pair.get("baseToken", {}).get("symbol", "TOKEN"),
                                                    "source": f"DexScreener ({main_pair.get('dexId', 'DEX')})",
                                                    "price_usd": price_usd,
                                                    "liquidity_usd": liquidity_usd,
                                                    "holders": [],
                                                    "trades": []
                                                }
                                                await callback(token_info)

                        elif res.status_code == 429:
                            await asyncio.sleep(20)

                    except Exception as e:
                        logger.error(f"⚠️ Errore scanner: {e}")
                    
                    await asyncio.sleep(8)

        except Exception as crash_error:
            await asyncio.sleep(5)