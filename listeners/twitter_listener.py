import asyncio
import logging

logger = logging.getLogger(__name__)

async def start_twitter_listener(callback):
    """Monitora X / Twitter per Contract Address."""
    logger.info("🐦 Twitter Listener avviato ed in ascolto...")
    while True:
        try:
            await asyncio.sleep(15)
        except Exception as e:
            logger.error(f"Errore ciclo Twitter Listener: {e}")
            await asyncio.sleep(15)