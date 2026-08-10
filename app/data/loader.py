import json
import logging
import os
from app.config import settings
from app.data.book_index import book_index
from app.data.market_index import market_index

logger = logging.getLogger(__name__)

def load_data():
    book_path = settings.BOOK_PATH
    market_path = settings.MARKET_PATH

    logger.info(f"Loading client book from {book_path}...")
    if os.path.exists(book_path):
        with open(book_path, "r", encoding="utf-8") as f:
            book_data = json.load(f)
            book_index.load(book_data)
    else:
        logger.warning(f"File not found: {book_path}")

    logger.info(f"Loading market data from {market_path}...")
    if os.path.exists(market_path):
        with open(market_path, "r", encoding="utf-8") as f:
            market_data = json.load(f)
            market_index.load(market_data)
    else:
        logger.warning(f"File not found: {market_path}")
