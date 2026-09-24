import asyncio
import logging
import aiohttp

logger = logging.getLogger(__name__)

async def listen_dexscreener(callback):
    """Monitora e recupera le informazioni estese delle coppie recenti."""
    latest_url = "https://api.dexscreener.com/token-profiles/latest/v1"
    pairs_url = "https://api.dexscreener.com/latest/dex/tokens/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    seen_tokens = set()
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(latest_url, headers=headers) as resp:
                    if resp.status == 200:
                        profiles = await resp.json()
                        for item in profiles:
                            token_id = item.get("tokenAddress")
                            if item.get("chainId") == "solana" and token_id not in seen_tokens:
                                seen_tokens.add(token_id)
                                
                                # Recupera i dati del pair (liquidità e market cap)
                                async with session.get(f"{pairs_url}{token_id}", headers=headers) as p_resp:
                                    if p_resp.status == 200:
                                        p_data = await p_resp.json()
                                        pairs = p_data.get("pairs")
                                        if pairs:
                                            await callback(pairs[0])
                                            # Pausa per evitare errori HTTP 429 su Telegram
                                            await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Errore recupero token: {e}")
            
            await asyncio.sleep(5)
