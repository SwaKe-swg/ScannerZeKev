import asyncio
import logging
from telegram import Bot
from config import Config

logger = logging.getLogger(__name__)

async def send_telegram_alert(message: str):
    """Invia un messaggio di testo al canale o chat configurata."""
    if not Config.TELEGRAM_BOT_TOKEN or not Config.TELEGRAM_CHAT_ID:
        logger.error("Token o Chat ID non configurati correttamente.")
        return False
        
    try:
        bot = Bot(token=Config.TELEGRAM_BOT_TOKEN)
        await bot.send_message(
            chat_id=Config.TELEGRAM_CHAT_ID,
            text=message,
            parse_mode="Markdown"
        )
        logger.info("Notifica Telegram inviata con successo.")
        return True
    except Exception as e:
        logger.error(f"Errore durante l'invio del messaggio Telegram: {e}")
        return False
